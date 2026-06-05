import asyncio
import os
import sys
import io
import time
import pandas as pd
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.insert(0, script_dir)

os.environ["ENGINE_MODE"] = "HF_PIPELINE"
load_dotenv(os.path.join(script_dir, ".env"), override=True)
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

from app.security_core import check_security, security_lifespan
from fastapi import HTTPException

# 파일 목록
TEST_DIR = "tests/qa_tester/test_data"
ENGLISH_FILES = [
    "phase1_English.csv", # Phase 1: NORMAL
    "phase2_English.csv", # Phase 2: LEAK_PLAIN (기밀 유출)
    "phase3_English.csv", # Phase 3: LEAK_EVASION (우회 유출)
    "phase4_English.csv", # Phase 4: INJECTION (악성 인젝션/시스템 장악)
]

async def process_prompt(sem, index, phase_num, expected, prompt_text):
    """비동기 병렬로 Ollama에 요청을 보내 처리 결과를 반환"""
    async with sem:
        result = {
            "index": index,
            "phase": phase_num,
            "expected_label": expected,
            "original_prompt": prompt_text,
            "status": "ALLOWED",
            "reason": ""
        }
        
        try:
            # check_security가 마스킹까지 수행함
            # 악성(BLOCKED) 판정 시 HTTPException(403) 발생
            security_res = await check_security(prompt_text)
            
            # 마스킹 여부 확인
            if security_res.get("mapping") and len(security_res.get("mapping")) > 0:
                result["status"] = "MASKED"
                
        except HTTPException as e:
            if e.status_code == 403:
                result["status"] = "BLOCKED"
                result["reason"] = str(e.detail)
            else:
                result["status"] = "ERROR"
                result["reason"] = str(e.detail)
        except Exception as e:
            result["status"] = "ERROR"
            result["reason"] = str(e)
            

        # 터미널 진행 상황 출력
        print(f"✅ [{index + 1}/600] 검증 완료 (Phase {phase_num} - 결과: {result['status']})", flush=True)
        return result

async def run_english_bulk_test():
    print("=" * 60)
    print("🚀 [대규모 검증] 영어 프롬프트 600개 V4 파이프라인 테스트 시작")
    print("=" * 60)
    
    # 1. 데이터 로드 및 확인
    all_prompts = []
    
    for fname in ENGLISH_FILES:
        path = os.path.join(TEST_DIR, fname)
        try:
            df = pd.read_csv(path, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding='cp949')
        print(f"✅ {fname} 로드 완료 (총 {len(df)}건)")
        
        # 파일별로 프롬프트의 형태/위협 유형(Phase)이 다른지 체크
        for _, row in df.iterrows():
            phase_num = row.get("phase", fname.replace(".csv", ""))
            expected = row.get("expected_label", "UNKNOWN")
            prompt = str(row.get("original_prompt", ""))
            
            # phase1은 NORMAL, 2~4는 공격(유출, 인젝션)
            all_prompts.append((phase_num, expected, prompt))
            
    print(f"\n총 {len(all_prompts)}개의 영어 프롬프트가 병합되었습니다.")
    print("Ollama(Qwen2.5)에 대한 비동기 병렬 처리를 시작합니다. (약 3~5분 소요 예상)")
    print("-" * 60)
    
    start_time = time.time()
    
    results = []
    # 한 번에 1개씩 순차 처리하여 로컬 서버 타임아웃 방지
    semaphore = asyncio.Semaphore(1)
    
    async with security_lifespan(None):
        for idx, (p_num, expected, text) in enumerate(all_prompts):
            # 순차 처리 및 즉시 저장(Incremental Save) 적용
            res = await process_prompt(semaphore, idx, p_num, expected, text)
            results.append(res)
            
            # 한 건 처리될 때마다 즉시 CSV에 덮어쓰기/이어쓰기 (오류로 튕겨도 기록 보존)
            df_temp = pd.DataFrame([res])
            write_mode = 'w' if idx == 0 else 'a'
            write_header = True if idx == 0 else False
            df_temp.to_csv("english_v4_test_results.csv", mode=write_mode, header=write_header, index=False, encoding='utf-8-sig')
            
    end_time = time.time()
    print(f"\n✅ 600개 프롬프트 검증 완료! (총 소요 시간: {end_time - start_time:.2f}초)")
    print("결과가 'english_v4_test_results.csv'에 최종 저장되었습니다.\n")
    
    df_res = pd.DataFrame(results)
    
    print("=" * 60)
    print("📊 [영어 600개 통합 테스트 결과 (Phase 1~4)]")
    print("=" * 60)
    
    # NORMAL vs MALICIOUS 분류
    # Phase 1 = NORMAL
    # Phase 2, 3, 4 = 악성(유출 및 인젝션 방어 대상)
    df_normal = df_res[df_res['phase'] == 1]
    df_malicious = df_res[df_res['phase'].isin([2, 3, 4])]
    
    # 정상 통과(TN) 및 오탐(FP)
    tn = len(df_normal[df_normal['status'].isin(['ALLOWED', 'MASKED'])])
    fp = len(df_normal[df_normal['status'] == 'BLOCKED'])
    
    # 악성 차단/마스킹(TP) 및 미탐(FN)
    tp = len(df_malicious[df_malicious['status'].isin(['BLOCKED', 'MASKED'])])
    fn = len(df_malicious[df_malicious['status'] == 'ALLOWED'])
    
    print(f"  - 정탐(TP, 악성 차단/마스킹): {tp} / {len(df_malicious)}")
    print(f"  - 미탐(FN, 보안 뚫림)      : {fn} / {len(df_malicious)}")
    print(f"  - 정답(TN, 정상 통과)      : {tn} / {len(df_normal)}")
    print(f"  - 오탐(FP, 정상 차단)      : {fp} / {len(df_normal)}")
    print("-" * 60)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    accuracy = (tp + tn) / len(df_res)
    
    print(f"  ▶ 방어율 (Recall)  : {recall * 100:.1f}%")
    print(f"  ▶ 정밀도 (Precision): {precision * 100:.1f}%")
    print(f"  ▶ 정확도 (Accuracy) : {accuracy * 100:.1f}%")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_english_bulk_test())
