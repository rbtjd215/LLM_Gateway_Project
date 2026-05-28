#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_e2e_reverse_substitution.py
────────────────────────────────────────────────────────────────────────────
AutoCore AI 보안 게이트웨이 - 역치환(De-masking) E2E 검증 스크립트

이 테스트 스크립트는 두 가지 환경 모두에서 역치환 성능을 측정합니다:
  1. Mock LLM 모드 (USE_MOCK_LLM=True) - 즉각적인 파이프라인 정합성 검증
  2. 실제 Gemini API 모드 (USE_MOCK_LLM=False) - 외부 LLM의 마스크 토큰 인지 및 복원력 검증

[테스트 설계 특징]
외부 LLM(Gemini)이 응답 본문 내에 마스킹된 토큰(예: __MASK_PER_xxx__)을 자연스럽게 
포함하도록 유도하기 위해, 프롬프트에 "코드명을 언급하며 답변해 달라"는 컨텍스트를 주입합니다.
────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000"
LOGIN_ENDPOINT = f"{BASE_URL}/login"
CHAT_ENDPOINT = f"{BASE_URL}/chat"

# 테스트용 계정 정보
TEST_USER = "EMP-001"
TEST_PASS = "pass1234"

# 테스트 데이터셋 정의 (기밀 유형별)
TEST_CASES = [
    {
        "id": "SUB-001",
        "category": "PER (사원번호)",
        "prompt": "다음 사내 인사평가 코멘트를 긍정/부정으로 분류하고 요약해줘. [대상자: EMP-123, 코멘트: 이 직원은 업무 처리가 빠르지만 소통이 부족함]. 답변에 반드시 '대상자 EMP-123의 평가 요약'이라는 문구를 포함해줘.",
        "expected_targets": ["EMP-123"],
    },
    {
        "id": "SUB-002",
        "category": "DWG (도면코드)",
        "prompt": "다음 설계 도면의 스펙을 보고 개선점을 1줄로 제시해줘. [도면: DWG-2026-ALPHA, 문제점: 내구성이 약함]. 답변에 반드시 '도면 DWG-2026-ALPHA 개선점'이라는 문구를 넣어줘.",
        "expected_targets": ["DWG-2026-ALPHA"],
    },
    {
        "id": "SUB-003",
        "category": "PHONE (전화번호)",
        "prompt": "다음 고객 불만 텍스트에서 감정을 분석해줘. [발신자: 010-1234-5678, 내용: 배송이 너무 늦어서 화가 납니다!]. 답변에 '연락처 010-1234-5678 고객의 감정은' 이라고 시작해줘.",
        "expected_targets": ["010-1234-5678"],
    },
    {
        "id": "SUB-004",
        "category": "DIM (치수/공차)",
        "prompt": "부품 스펙 텍스트를 영문으로 번역해줘. [해당 부품은 공차 ± 0.05 mm 를 엄격하게 준수해야 합니다]. 번역된 문장 뒤에 괄호로 (원본 스펙: 공차 ± 0.05 mm) 를 그대로 명시해줘.",
        "expected_targets": ["공차 ± 0.05 mm"],
    },
    {
        "id": "SUB-005",
        "category": "MULTIPLE (다중 기밀)",
        "prompt": "다음 회의록을 1줄로 요약해줘. [EMP-456 책임이 신규 도면 DWG-7777-BETA 설계안을 발표함]. 답변에 사번과 도면 코드를 그대로 포함해서 요약해줘.",
        "expected_targets": ["EMP-456", "DWG-7777-BETA"],
    }
]

def get_jwt_token() -> str:
    """FastAPI 보안 게이트웨이에 로그인하여 JWT 토큰을 취득합니다."""
    try:
        response = requests.post(
            LOGIN_ENDPOINT,
            data={"username": TEST_USER, "password": TEST_PASS},
            timeout=10
        )
        if response.status_code != 200:
            print(f"❌ [로그인 실패] 상태 코드: {response.status_code}")
            print(f"    상세 응답: {response.text}")
            sys.exit(1)
        
        token = response.json().get("access_token")
        return token
    except Exception as e:
        print(f"❌ [네트워크 에러] 로그인 서버에 접속할 수 없습니다: {e}")
        sys.exit(1)

def run_e2e_tests(token: str) -> bool:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    use_mock = os.getenv("USE_MOCK_LLM", "True")
    engine_mode = os.getenv("ENGINE_MODE", "REGEX")
    
    print("\n" + "="*80)
    print(f" 🚀 AI 보안 게이트웨이 역치환 E2E 테스트 시작")
    print(f"    - 백엔드 주소: {BASE_URL}")
    print(f"    - ENGINE_MODE: {engine_mode}")
    print(f"    - USE_MOCK_LLM (Gemini Mock 여부): {use_mock}")
    print("="*80 + "\n")
    
    success_count = 0
    total_cases = len(TEST_CASES)
    
    for case in TEST_CASES:
        print(f"[{case['id']}] {case['category']} 테스트 케이스 실행")
        print(f"  📥 입력 프롬프트: {case['prompt']}")
        
        start_time = time.time()
        try:
            response = requests.post(
                CHAT_ENDPOINT,
                json={"prompt": case['prompt']},
                headers=headers,
                timeout=120  # LLM 추론 시간 감안
            )
            elapsed_time = time.time() - start_time
            
            # API 호출 상태 코드 체크
            if response.status_code != 200:
                print(f"  ❌ [FAIL] API 응답 에러 (HTTP {response.status_code}): {response.text}")
                print("-" * 60)
                continue
                
            res_data = response.json()
            ai_response = res_data.get("response", "")
            mask_session_id = response.headers.get("X-Mask-Session-Id", "N/A")
            
            print(f"  📤 최종 복원 응답: {ai_response}")
            print(f"  ⏱️ 소요 시간: {elapsed_time:.2f}초")
            print(f"  🔑 마스크 세션 ID: {mask_session_id}")
            
            # 역치환 타겟 복원 여부 확인
            all_restored = True
            for target in case['expected_targets']:
                if target in ai_response:
                    print(f"  ✅ [SUCCESS] 기밀 데이터 '{target}' 복원 완료")
                else:
                    print(f"  ❌ [FAIL] 기밀 데이터 '{target}' 복원 실패 (최종 응답에 원본이 보이지 않음)")
                    all_restored = False
            
            if all_restored:
                success_count += 1
                
        except requests.exceptions.Timeout:
            print("  ❌ [FAIL] 요청 타임아웃 초과 (120초)")
        except Exception as e:
            print(f"  ❌ [FAIL] 테스트 중 예외 발생: {e}")
            
        print("-" * 80)
        time.sleep(1) # 부하 방지용 짧은 딜레이
        
    print("\n" + "="*80)
    success_rate = (success_count / total_cases) * 100
    print(f" 📊 E2E 역치환 검증 결과 요약")
    print(f"    - 총 실행 건수: {total_cases} 건")
    print(f"    - 성공 건수: {success_count} 건")
    print(f"    - 실패 건수: {total_cases - success_count} 건")
    print(f"    - 역치환 성공률: {success_rate:.1f}%")
    print("="*80 + "\n")
    
    return success_count == total_cases

def main():
    token = get_jwt_token()
    success = run_e2e_tests(token)
    if success:
        print("🎉 [패스] 모든 역치환 시나리오가 성공적으로 완결되었습니다!")
        sys.exit(0)
    else:
        print("⚠️ [경고] 일부 역치환 시나리오에서 복원 실패가 감지되었습니다. 로그를 확인하세요.")
        sys.exit(1)

if __name__ == "__main__":
    main()
