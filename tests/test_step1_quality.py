import asyncio
import os
import sys
import io
import time
from google import genai
from dotenv import load_dotenv

# Windows 터미널 유니코드(이모지) 출력 에러(cp949) 방지
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 스크립트 실행 위치 이슈(한글 경로) 방지를 위해 절대 경로로 작업 디렉토리 강제 변경
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.insert(0, script_dir)

# 환경변수 강제 설정 (HF_PIPELINE 모드 활성화)
os.environ["ENGINE_MODE"] = "HF_PIPELINE"
# override=True 를 설정하여 기존 캐시된 환경변수 무시하고 .env 파일 값 강제 로드
load_dotenv(os.path.join(script_dir, ".env"), override=True)

# 호스트 환경에서 파이썬 직접 실행 시 host.docker.internal 이슈 방지를 위해 localhost 강제 지정
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

from app.security_core import check_security, unmask_response, security_lifespan

# 제미나이 클라이언트 초기화
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("[ERROR] GEMINI_API_KEY가 .env에 설정되어 있지 않습니다.")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)
# [중요] 2026년 환경에 맞춰 routers.py와 동일한 최신 모델 사용
MODEL_NAME = "gemini-3-flash-preview"  

# 테스트 시나리오용 기밀 문서 3건
TEST_DOCUMENTS = [
    {
        "title": "시나리오 1: 핵심 소재 배합비가 포함된 회의록 요약",
        "content": "2026년 5월 10일 제품개발부서 회의록입니다. 이번 신형 배터리 팩에는 에너지 밀도를 높이기 위해 Titanium 45%와 R-134a 70%를 혼합한 신소재를 적용하기로 결정했습니다. 또한 EMP-001 연구원의 제안에 따라 내부 압력 한계치는 3.5MPa로 설정되었습니다. 이 문서를 3줄로 요약해주세요."
    },
    {
        "title": "시나리오 2: 차세대 프로젝트 코드가 포함된 기획서 번역",
        "content": "Project Delta의 초기 기획안입니다. 이 프로젝트의 핵심 부품인 DWG-1001-A는 공차 ±0.005mm의 초정밀 가공이 필요하며, 예상 매출은 약 5억 원(Revenue 5M)으로 기대됩니다. 이 내용을 영어로 번역해주세요."
    },
    {
        "title": "시나리오 3: 개인정보 및 단가가 포함된 영업 보고서 요약",
        "content": "2분기 영업 실적 보고입니다. 주요 고객사와의 협상 결과, 주력 모델의 납품 단가는 개당 3000원으로 확정되었습니다. 관련 계약 책임자는 김철수(EMP-204)이며, 긴급 연락처는 010-1234-5678입니다. 이 보고서의 핵심 내용을 요약해주세요."
    }
]

def call_gemini(prompt: str) -> str:
    """Gemini API 호출 래퍼 (에러 처리 포함)"""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"[Gemini API Error] {e}"

async def run_test():
    print("=" * 60)
    print("[Phase 1] AutoCore 게이트웨이 요약/번역 품질 검증 테스트 시작")
    print("=" * 60)
    
    # SecurityCore 초기화 (Ollama 연결 풀 생성 등)
    async with security_lifespan(None):
        for idx, doc in enumerate(TEST_DOCUMENTS, 1):
            print(f"\n\n▶▶ {doc['title']} ◀◀")
            print(f"■ 원본 문서:\n{doc['content']}\n")
            
            # 1. 대조군: 게이트웨이 없이 바로 Gemini 전송
            print("[대조군] 게이트웨이 없이 원본 문서 요약 중...")
            baseline_summary = call_gemini(doc['content'])
            print(f"[결과] 대조군 요약/번역 결과:\n{baseline_summary}\n")
            
            # API Rate Limit 방지용 대기
            time.sleep(3)
            
            # 2. 실험군: AutoCore 게이트웨이 파이프라인 적용
            print("[실험군] AutoCore 마스킹 진행 중...")
            try:
                security_result = await check_security(doc['content'])
                masked_text = security_result["masked_text"]
                mapping = security_result["mapping"]
                
                print(f"[마스킹 결과] (외부로 전송되는 텍스트):\n{masked_text}")
                print(f"[마스킹 매핑 정보]:\n{mapping}\n")
                
                print("[실험군] 마스킹된 텍스트로 Gemini 요약/번역 요청 중...")
                masked_summary = call_gemini(masked_text)
                
                print("[실험군] 역치환(Unmasking) 진행 중...")
                final_unmasked_summary = unmask_response(masked_summary, mapping)
                
                print(f"[최종 결과] 실험군 역치환 최종 요약/번역 결과 (사용자가 보는 화면):\n{final_unmasked_summary}\n")
                
            except Exception as e:
                print(f"[ERROR] 파이프라인 에러 발생: {e}")
            
            print("-" * 60)
            if idx < len(TEST_DOCUMENTS):
                print("API 한도 방지를 위해 5초 대기합니다...")
                time.sleep(5)
                
    print("\n모든 테스트가 완료되었습니다. 대조군과 실험군의 품질을 비교해보세요!")

if __name__ == "__main__":
    asyncio.run(run_test())
