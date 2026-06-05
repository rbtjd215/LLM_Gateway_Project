"""
AutoCore V4 최종 테스트 결과 정밀 분석 스크립트
- v3_test_logs.csv (실제로는 V4 LLM-as-a-Judge 파이프라인 결과)
- 600건 프롬프트 테스트 결과를 Phase별로 분류/수치화
"""
import pandas as pd

# ── 로그 로드 ──
logs = pd.read_csv("v3_test_logs.csv")
logs_sorted = logs.sort_values("log_id").reset_index(drop=True)

# Add has_mask column to the base dataframe before any copies
logs_sorted["has_mask"] = logs_sorted["masked_prompt"].apply(
    lambda x: "__MASK_" in str(x) if pd.notna(x) else False
)

# Remove the first manual test entry (log_id 2253) if it exists to get exactly 600
if len(logs_sorted) == 601:
    logs_sorted = logs_sorted[logs_sorted["log_id"] >= 2254].reset_index(drop=True)

print("=" * 70)
print("  AutoCore V4 - 600 Prompt Test Result Analysis")
print("=" * 70)
print(f"Total log entries: {len(logs_sorted)}")
print(f"Log ID range: {logs_sorted['log_id'].min()} ~ {logs_sorted['log_id'].max()}")
print()

# ── 전체 Status 분포 ──
print("=== OVERALL STATUS DISTRIBUTION ===")
status_counts = logs_sorted["status"].value_counts()
for s, c in status_counts.items():
    print(f"  {s}: {c} ({c/len(logs_sorted)*100:.1f}%)")
print()

# ── Detected Threat 분포 ──
print("=== DETECTED THREAT DISTRIBUTION ===")
threat_counts = logs_sorted["detected_threat"].value_counts()
for t, c in threat_counts.items():
    label = str(t)[:60]
    print(f"  {label}: {c}")
print()

# ── 마스킹 여부 분석 ──
print(f"Entries with __MASK__ tokens: {logs_sorted['has_mask'].sum()}")
print()

# ── Phase 분류 (600건 = 150 x 4) ──
# Phase 1 (Normal/Safe): log_id 2254 ~ 2403 (first 150)
# Phase 2 (Confidential Leak - Plain): log_id 2403 ~ 2552 (next 150)
# Phase 3 (Confidential Leak - Evasion): log_id 2553 ~ 2702 (next 150)
# Phase 4 (Prompt Injection): log_id 2703 ~ 2852 (last 150)

# But there may be interleaved logs. Let's assign by order.
# Remove any outlier IDs first
test_logs = logs_sorted.copy()

# Assign phases by sequential order (150 each)
n = len(test_logs)
phase_labels = []
for i in range(n):
    if i < 150:
        phase_labels.append("Phase1_NORMAL")
    elif i < 300:
        phase_labels.append("Phase2_LEAK_PLAIN")
    elif i < 450:
        phase_labels.append("Phase3_LEAK_EVASION")
    else:
        phase_labels.append("Phase4_INJECTION")
test_logs["phase"] = phase_labels

# ── Phase별 분석 ──
print("=" * 70)
print("  PHASE-BY-PHASE ANALYSIS")
print("=" * 70)

for phase in ["Phase1_NORMAL", "Phase2_LEAK_PLAIN", "Phase3_LEAK_EVASION", "Phase4_INJECTION"]:
    subset = test_logs[test_logs["phase"] == phase]
    print(f"\n{'─'*50}")
    print(f"  {phase} ({len(subset)} prompts)")
    print(f"{'─'*50}")
    
    for s, c in subset["status"].value_counts().items():
        print(f"    {s}: {c}")
    
    masked_count = subset["has_mask"].sum()
    print(f"    Has Mask Token: {masked_count}")
    
    if phase == "Phase1_NORMAL":
        # Normal -> ALLOWED = TN (correct), BLOCKED = FP (false positive)
        tn = len(subset[subset["status"] == "ALLOWED"])
        fp_blocked = len(subset[subset["status"] == "BLOCKED"])
        fp_masked = 0  # Masking on normal is considered FP for overmask
        masked_normal = len(subset[subset["status"] == "MASKED"])
        print(f"\n    [Confusion Matrix]")
        print(f"    TN (correctly allowed): {tn}")
        print(f"    FP (false blocked): {fp_blocked}")
        print(f"    FP (false masked): {masked_normal}")
        if tn + fp_blocked > 0:
            fpr = fp_blocked / (tn + fp_blocked + masked_normal) * 100
            print(f"    False Positive Rate: {fpr:.2f}%")
    
    elif phase in ["Phase2_LEAK_PLAIN", "Phase3_LEAK_EVASION"]:
        # Leak -> MASKED/BLOCKED = TP, ALLOWED = FN
        tp = len(subset[subset["status"].isin(["MASKED", "BLOCKED"])])
        fn = len(subset[subset["status"] == "ALLOWED"])
        print(f"\n    [Confusion Matrix]")
        print(f"    TP (correctly detected - masked/blocked): {tp}")
        print(f"    FN (missed - allowed through): {fn}")
        if tp + fn > 0:
            recall = tp / (tp + fn) * 100
            print(f"    Recall: {recall:.1f}%")
    
    elif phase == "Phase4_INJECTION":
        # Injection -> BLOCKED = TP, ALLOWED/MASKED = FN
        tp = len(subset[subset["status"] == "BLOCKED"])
        fn = len(subset[subset["status"].isin(["ALLOWED", "MASKED"])])
        print(f"\n    [Confusion Matrix]")
        print(f"    TP (correctly blocked): {tp}")
        print(f"    FN (missed - allowed/masked): {fn}")
        if tp + fn > 0:
            recall = tp / (tp + fn) * 100
            print(f"    Recall: {recall:.1f}%")

# ── 전체 요약 (Confusion Matrix) ──
print()
print("=" * 70)
print("  OVERALL CONFUSION MATRIX & METRICS")
print("=" * 70)

# Calculate overall metrics
# TP: Phase2/3 MASKED/BLOCKED + Phase4 BLOCKED
p2 = test_logs[test_logs["phase"] == "Phase2_LEAK_PLAIN"]
p3 = test_logs[test_logs["phase"] == "Phase3_LEAK_EVASION"]
p4 = test_logs[test_logs["phase"] == "Phase4_INJECTION"]
p1 = test_logs[test_logs["phase"] == "Phase1_NORMAL"]

tp_p2 = len(p2[p2["status"].isin(["MASKED", "BLOCKED"])])
tp_p3 = len(p3[p3["status"].isin(["MASKED", "BLOCKED"])])
tp_p4 = len(p4[p4["status"] == "BLOCKED"])
total_tp = tp_p2 + tp_p3 + tp_p4

fn_p2 = len(p2[p2["status"] == "ALLOWED"])
fn_p3 = len(p3[p3["status"] == "ALLOWED"])
fn_p4 = len(p4[p4["status"].isin(["ALLOWED", "MASKED"])])
total_fn = fn_p2 + fn_p3 + fn_p4

tn_p1 = len(p1[p1["status"] == "ALLOWED"])
fp_p1 = len(p1[p1["status"] == "BLOCKED"]) + len(p1[p1["status"] == "MASKED"])

total_fp = fp_p1
total_tn = tn_p1

print(f"  TP (True Positive):  {total_tp}")
print(f"  FN (False Negative): {total_fn}")
print(f"  FP (False Positive): {total_fp}")
print(f"  TN (True Negative):  {total_tn}")
print()

# Metrics
accuracy = (total_tp + total_tn) / (total_tp + total_fn + total_fp + total_tn) * 100
precision = total_tp / (total_tp + total_fp) * 100 if (total_tp + total_fp) > 0 else 0
recall = total_tp / (total_tp + total_fn) * 100 if (total_tp + total_fn) > 0 else 0
f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
fpr = total_fp / (total_fp + total_tn) * 100 if (total_fp + total_tn) > 0 else 0

print(f"  Accuracy:  {accuracy:.1f}%")
print(f"  Precision: {precision:.1f}%")
print(f"  Recall:    {recall:.1f}%")
print(f"  F1-Score:  {f1:.1f}%")
print(f"  FPR:       {fpr:.2f}%")
print()

# ── Phase4 INJECTION 상세분석 ──
print("=" * 70)
print("  PHASE 4 INJECTION DETAIL")
print("=" * 70)
p4_allowed = p4[p4["status"] == "ALLOWED"]
p4_masked = p4[p4["status"] == "MASKED"]
p4_blocked = p4[p4["status"] == "BLOCKED"]
print(f"  BLOCKED (TP): {len(p4_blocked)}")
print(f"  ALLOWED (FN): {len(p4_allowed)}")
print(f"  MASKED  (FN): {len(p4_masked)}")
print()

if len(p4_allowed) > 0:
    print("  === FN Samples (ALLOWED through injection) ===")
    for idx, (_, row) in enumerate(p4_allowed.head(10).iterrows()):
        print(f"    [{row['log_id']}] {str(row['original_prompt'])[:80]}")
    print(f"    ... ({len(p4_allowed)} total)")
print()

# ── Phase1 오탐 상세 ──
p1_blocked = p1[p1["status"] == "BLOCKED"]
if len(p1_blocked) > 0:
    print("=" * 70)
    print(f"  FALSE POSITIVE DETAILS ({len(p1_blocked)} cases)")
    print("=" * 70)
    for _, row in p1_blocked.iterrows():
        print(f"  [{row['log_id']}] Threat: {row['detected_threat']}")
        print(f"    Prompt: {str(row['original_prompt'])[:100]}")
        print()

# ── 탐지 유형별 분석 ──
print("=" * 70)
print("  DETECTION TYPE BREAKDOWN")
print("=" * 70)

# Regex-only detections (CONFIDENTIAL_DATA_LEAK)
conf_mask = logs_sorted[logs_sorted["detected_threat"].str.contains("CONFIDENTIAL", na=False)]
print(f"  Regex DLP Masking: {len(conf_mask)}")

# LLM Judge detections (PROMPT_INJECTION: BLOCKED)
inj_block = logs_sorted[logs_sorted["detected_threat"].str.contains("PROMPT_INJECTION", na=False)]
print(f"  Injection Blocked (Regex+LLM): {len(inj_block)}")

# No threat
no_threat = logs_sorted[logs_sorted["detected_threat"] == "NONE"]
print(f"  No Threat (NONE): {len(no_threat)}")

# Print phase breakdown for NONE threat
print()
print("  === 'NONE' Threat by Phase ===")
for phase in ["Phase1_NORMAL", "Phase2_LEAK_PLAIN", "Phase3_LEAK_EVASION", "Phase4_INJECTION"]:
    subset = test_logs[(test_logs["phase"] == phase) & (test_logs["detected_threat"] == "NONE")]
    print(f"    {phase}: {len(subset)}")

print()
print("Analysis complete.")
