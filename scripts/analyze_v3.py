"""V3 테스트 결과 분석 스크립트"""
import pandas as pd
import os

# ── 원본 테스트 데이터 로드 (Phase 정보 추출) ──
test_dir = "tests/qa_tester/test_data"
phase_files = {
    "NORMAL": "phase1_leechoungwon.csv",
    "LEAK_PLAIN": "phase2_leechoungwon.csv",
    "LEAK_EVASION": "phase3_seonhyo.csv",
    "INJECTION": "phase4_seonhyo.cvs.csv",
}

all_prompts = []
for phase, fname in phase_files.items():
    path = os.path.join(test_dir, fname)
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except:
        df = pd.read_csv(path, encoding="cp949")
    
    print(f"--- {fname} ---")
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {df.columns.tolist()}")
    
    # 컬럼 중 'original_prompt' 또는 'prompt'가 있는지 확인
    prompt_col = None
    for col in df.columns:
        if 'prompt' in col.lower() or 'text' in col.lower():
            prompt_col = col
            break
    if not prompt_col:
        prompt_col = df.columns[-1] # fallback

    for _, row in df.iterrows():
        prompt_text = str(row[prompt_col]).strip()
        if prompt_text and prompt_text != 'nan':
            all_prompts.append({
                "phase": phase,
                "prompt": prompt_text,
            })
    print(f"  Phase '{phase}': {len(df)} prompts loaded (using column '{prompt_col}')")
    print()

print(f"Total test prompts: {len(all_prompts)}")
print()

# ── 서버 로그 로드 ──
logs = pd.read_csv("v3_test_logs.csv")
print(f"Total server logs: {len(logs)}")
print()

# ── 매핑: 원본 프롬프트 -> 로그 결과 ──
# 먼저 앞 4건(수동 테스트)과 마지막 1건 제거 시도
# log_id 순서대로 CSV 테스트 건과 매핑

# log_id로 정렬
logs_sorted = logs.sort_values("log_id").reset_index(drop=True)

# 수동 테스트 건 제거를 위해 분석
print("=== Log ID range ===")
print(f"  Min: {logs_sorted['log_id'].min()}, Max: {logs_sorted['log_id'].max()}")
print()

# 수동 테스트(이전 세션)를 제거하기 위해, 
# tester.py는 Phase1 -> Phase2 -> Phase3 -> Phase4 순서로 전송
# 처음 3건은 수동 테스트였을 가능성이 있으므로
# 전체 로그에서 처음 몇건이 수동 테스트인지 확인

print("=== First 10 logs (check for manual tests) ===")
for i, row in logs_sorted.head(10).iterrows():
    prompt = str(row.get("original_prompt", ""))[:80]
    print(f"  [{row['log_id']}] {row['status']}: {prompt}")
print()

print("=== Status Distribution ===")
print(logs_sorted["status"].value_counts().to_string())
print()

# ── 프롬프트 기반 매칭 ──
# 로그의 original_prompt와 테스트 프롬프트를 매칭
prompt_to_phase = {}
for p in all_prompts:
    prompt_to_phase[p["prompt"]] = p["phase"]

matched = 0
unmatched_logs = 0
results = []

for _, row in logs_sorted.iterrows():
    orig = str(row.get("original_prompt", "")).strip()
    phase = prompt_to_phase.get(orig, None)
    
    if phase is None:
        # 부분 매칭 시도 (인코딩 이슈로 첫 20자 매칭)
        for p_text, p_phase in prompt_to_phase.items():
            if len(orig) > 10 and len(p_text) > 10:
                if orig[:20] == p_text[:20]:
                    phase = p_phase
                    break
    
    if phase:
        matched += 1
        results.append({
            "log_id": row["log_id"],
            "phase": phase,
            "status": row["status"],
            "detected_threat": row.get("detected_threat", ""),
            "prompt_preview": orig[:60],
        })
    else:
        unmatched_logs += 1

print(f"=== Matching Results ===")
print(f"  Matched: {matched}")
print(f"  Unmatched: {unmatched_logs}")
print()

if not results:
    print("WARNING: No matches found. Trying alternative approach...")
    print("Assigning phases by order (Phase1: 1-150, Phase2: 151-300, etc.)")
    
    # 수동 테스트 건 제거: 처음 3건은 수동 테스트였을 가능성
    # tester가 Phase1부터 순서대로 전송하므로 순서 기반 할당
    # 첫 번째 수동테스트 식별 - 2253 ID는 V2 테스트의 마지막 항목이므로 제외
    
    # 수동 테스트(V3 초기 확인용 3건 제거)
    auto_logs = logs_sorted[logs_sorted["log_id"] > 2253].copy()
    auto_logs = auto_logs[auto_logs["log_id"] < 2760].reset_index(drop=True)
    
    print(f"  Auto-test logs (after filtering): {len(auto_logs)}")
    
    phases_order = []
    for phase in ["NORMAL", "LEAK_PLAIN", "LEAK_EVASION", "INJECTION"]:
        count = len([p for p in all_prompts if p["phase"] == phase])
        phases_order.extend([phase] * count)
    
    for i, (_, row) in enumerate(auto_logs.iterrows()):
        if i < len(phases_order):
            results.append({
                "log_id": row["log_id"],
                "phase": phases_order[i],
                "status": row["status"],
                "detected_threat": row.get("detected_threat", ""),
                "prompt_preview": str(row.get("original_prompt", ""))[:60],
            })
    
    print(f"  Assigned: {len(results)}")
    print()

# ── Phase별 분석 ──
rdf = pd.DataFrame(results)

print("=" * 70)
print("  V3 HYBRID PIPELINE - PHASE별 분석 결과")
print("=" * 70)

for phase in ["NORMAL", "LEAK_PLAIN", "LEAK_EVASION", "INJECTION"]:
    subset = rdf[rdf["phase"] == phase]
    if len(subset) == 0:
        print(f"\n[{phase}] No data")
        continue
    
    print(f"\n{'='*50}")
    print(f"  Phase: {phase} ({len(subset)} prompts)")
    print(f"{'='*50}")
    print(subset["status"].value_counts().to_string())
    
    # 혼동 행렬 계산
    if phase == "NORMAL":
        # 정상 -> ALLOWED/MASKED = Correct, BLOCKED = FP(오탐)
        tp = 0  # N/A for normal
        tn = len(subset[subset["status"].isin(["ALLOWED", "MASKED"])])
        fp = len(subset[subset["status"] == "BLOCKED"])
        fn = 0
        print(f"\n  [혼동행렬] TN(정상통과): {tn}, FP(오탐-차단): {fp}")
        if tn + fp > 0:
            print(f"  오탐률(FPR): {fp/(tn+fp)*100:.1f}%")
    
    elif phase in ["LEAK_PLAIN", "LEAK_EVASION"]:
        # 유출 시도 -> MASKED = TP, BLOCKED = TP, ALLOWED = FN(미탐)
        tp = len(subset[subset["status"].isin(["MASKED", "BLOCKED"])])
        fn = len(subset[subset["status"] == "ALLOWED"])
        print(f"\n  [혼동행렬] TP(탐지-마스킹/차단): {tp}, FN(미탐-통과): {fn}")
        if tp + fn > 0:
            print(f"  탐지율(Recall): {tp/(tp+fn)*100:.1f}%")
    
    elif phase == "INJECTION":
        # 인젝션 -> BLOCKED = TP, ALLOWED/MASKED = FN(미탐)
        tp = len(subset[subset["status"] == "BLOCKED"])
        fn = len(subset[subset["status"].isin(["ALLOWED", "MASKED"])])
        print(f"\n  [혼동행렬] TP(차단): {tp}, FN(미탐-통과): {fn}")
        if tp + fn > 0:
            print(f"  탐지율(Recall): {tp/(tp+fn)*100:.1f}%")

# ── 전체 요약 ──
print()
print("=" * 70)
print("  전체 요약")
print("=" * 70)
total = len(rdf)
blocked = len(rdf[rdf["status"] == "BLOCKED"])
masked = len(rdf[rdf["status"] == "MASKED"])
allowed = len(rdf[rdf["status"] == "ALLOWED"])
print(f"  총 처리 건수: {total}")
print(f"  BLOCKED: {blocked} ({blocked/total*100:.1f}%)")
print(f"  MASKED:  {masked} ({masked/total*100:.1f}%)")
print(f"  ALLOWED: {allowed} ({allowed/total*100:.1f}%)")

# Phase별 BLOCKED 상세 내역 (NORMAL에서 발생한 것 = FP)
normal_blocked = rdf[(rdf["phase"] == "NORMAL") & (rdf["status"] == "BLOCKED")]
if len(normal_blocked) > 0:
    print(f"\n=== 오탐(False Positive) 상세 ({len(normal_blocked)}건) ===")
    for _, row in normal_blocked.iterrows():
        print(f"  [{row['log_id']}] {row['detected_threat']}: {row['prompt_preview']}")

# INJECTION에서 ALLOWED된 것 = FN
inj_allowed = rdf[(rdf["phase"] == "INJECTION") & (rdf["status"] == "ALLOWED")]
if len(inj_allowed) > 0:
    print(f"\n=== 미탐(False Negative) - INJECTION에서 통과 ({len(inj_allowed)}건) ===")
    for _, row in inj_allowed.head(20).iterrows():
        print(f"  [{row['log_id']}] {row['prompt_preview']}")

# LEAK에서 ALLOWED된 것 = FN
leak_allowed = rdf[(rdf["phase"].isin(["LEAK_PLAIN", "LEAK_EVASION"])) & (rdf["status"] == "ALLOWED")]
if len(leak_allowed) > 0:
    print(f"\n=== 미탐(False Negative) - LEAK에서 통과 ({len(leak_allowed)}건) ===")
    for _, row in leak_allowed.head(20).iterrows():
        print(f"  [{row['log_id']}] [{row['phase']}] {row['prompt_preview']}")
