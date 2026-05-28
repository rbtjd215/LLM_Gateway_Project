import os
import time
import glob
import argparse
import pandas as pd
import requests

# 현재 스크립트 파일 위치를 기준으로 test_data 폴더 절대 경로 생성
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, 'test_data')

# 5000번이 아닌 실제 docker-compose의 8000번 포트로 수정
API_LOGIN_ENDPOINT = 'http://localhost:8000/login'
API_CHAT_ENDPOINT = 'http://localhost:8000/chat'

# DB에 존재하는 테스트용 관리자/사용자 계정 정보 (상황에 맞게 수정)
LOGIN_USER = 'EMP-001'
LOGIN_PASS = 'pass1234' # 테스트 환경에 맞게 입력 필요

# V4: Judge(1차) + GenMask(2차) = Ollama 2회 호출, 각 최대 30초 -> 최소 90초 필요
REQUEST_DELAY = 1.0

def get_auth_token(session: requests.Session) -> bool:
    """게이트웨이 로그인을 통해 JWT 토큰을 발급받아 세션 헤더에 등록합니다."""
    try:
        # OAuth2PasswordRequestForm 형식에 맞게 x-www-form-urlencoded 방식으로 전송
        response = session.post(
            API_LOGIN_ENDPOINT, 
            data={"username": LOGIN_USER, "password": LOGIN_PASS},
            timeout=5
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        print(f"[시스템] 로그인 성공! JWT 토큰이 세션에 적용되었습니다. (접속 계정: {LOGIN_USER})")
        return True
    except Exception as e:
        print(f"[인증 오류] 로그인 실패로 인해 테스트를 진행할 수 없습니다: {e}")
        return False

def run_automated_test(start_file=None, start_row=None, sample_size=None):
    # exist_ok=True를 통해 폴더 중복 생성 에러 방지
    os.makedirs(DATA_FOLDER, exist_ok=True)
    
    # 일관된 순서를 위해 정렬
    csv_files = sorted(glob.glob(os.path.join(DATA_FOLDER, "*.csv")))
    if not csv_files:
        print(f"[오류] '{DATA_FOLDER}' 폴더 내에 CSV 파일이 존재하지 않습니다. 파일을 넣고 다시 실행하십시오.")
        return

    print(f"[시스템] 총 {len(csv_files)}개의 CSV 파일을 발견했습니다. 순차 전송을 시작합니다.\n")
    
    total_processed = 0

    # Context Manager를 통한 소켓 자원 누수 방지
    with requests.Session() as session:
        
        # 1. JWT 토큰 발급 (필수)
        if not get_auth_token(session):
            return

        skip_file = bool(start_file)
        for file_path in csv_files:
            file_name = os.path.basename(file_path)
            
            if skip_file:
                if file_name != start_file:
                    continue
                skip_file = False  # 지정된 파일을 찾으면 스킵 해제
                
            print(f"\n▶ 실행 파일: {file_name}")
            
            try:
                # 인코딩 Fallback 로직 적용 (utf-8-sig 실패 시 cp949 재시도)
                try:
                    df = pd.read_csv(file_path, encoding='utf-8-sig')
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, encoding='cp949')

                if 'original_prompt' not in df.columns:
                    print(f"  [스킵] '{file_name}' 파일에 'original_prompt' 열이 없습니다.")
                    continue

                df = df.dropna(subset=['original_prompt'])
                
                # 샘플 사이즈가 지정된 경우, 파일당 앞에서부터 N개만 추출 (무작위가 아닌 순차)
                if sample_size is not None and sample_size > 0:
                    df = df.head(sample_size)
                    print(f"  [안내] 샘플 테스트 모드: 파일당 {sample_size}개만 테스트합니다.")

                file_total = len(df)
                file_success = 0
                
                for index, row in df.iterrows():
                    current_row = index + 2  # 헤더 포함 엑셀 행 번호 기준
                    
                    if start_row and file_name == start_file and current_row < start_row:
                        continue
                        
                    prompt_text = str(row['original_prompt']).strip()
                    if not prompt_text:
                        continue
                    
                    # 백엔드 스키마에 맞춰 prompt만 전송 (employee_num은 JWT에서 파싱됨)
                    payload = {"prompt": prompt_text}
                    
                    try:
                        response = session.post(API_CHAT_ENDPOINT, json=payload, timeout=90)
                        
                        # 토큰 만료(401) 시 재발급 후 재시도
                        if response.status_code == 401:
                            print("\n  [인증 만료] 토큰이 만료되었습니다. 재발급을 시도합니다...")
                            if get_auth_token(session):
                                response = session.post(API_CHAT_ENDPOINT, json=payload, timeout=90)
                            else:
                                print("  [치명적 오류] 토큰 재발급 실패. 테스트를 종료합니다.")
                                return

                        # 200(정상) 및 403(프롬프트 인젝션 방어 성공) 모두 성공으로 간주
                        if response.status_code in [200, 403]:
                            file_success += 1
                            total_processed += 1
                            # flush=True로 콘솔 출력 버퍼링 딜레이 방지
                            print(f"\r  전송 진행률: [{file_success}/{file_total}] 완료", end="", flush=True)
                        else:
                            print(f"\n  [경고] 행 {index+2} - 비정상 상태 반환: HTTP {response.status_code} / {response.text}")
                    
                    except requests.exceptions.RequestException as req_err:
                        print(f"\n  [네트워크 오류] 행 {index+2} 전송 실패: {req_err}")
                    
                    time.sleep(REQUEST_DELAY)
                    
                print(f"\n  파일 전송 완료. (성공: {file_success} / 전체: {file_total})")
                
            except Exception as e:
                print(f"\n  [파일 처리 오류] {file_name} 처리 중 문제 발생: {e}")

    print("\n==========================================")
    print(f"[시스템 종료] 모든 테스트가 완료되었습니다. 총 {total_processed}건의 데이터가 처리되었습니다.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoCore AI QA Tester")
    parser.add_argument("--start-file", type=str, help="이어하기를 시작할 파일명 (예: phase2_leechoungwon.csv)")
    parser.add_argument("--start-row", type=int, help="이어하기를 시작할 행 번호 (예: 47)")
    parser.add_argument("--sample-size", type=int, help="파일당 테스트할 샘플 개수 (빠른 검증용)")
    
    args = parser.parse_args()
    
    if args.start_row and not args.start_file:
        print("[경고] --start-row 옵션은 --start-file과 함께 사용해야 합니다.")
        exit(1)
        
    run_automated_test(
        start_file=args.start_file, 
        start_row=args.start_row,
        sample_size=args.sample_size
    )
