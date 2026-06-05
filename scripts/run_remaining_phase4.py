import os
import time
import pandas as pd
import requests

DATA_FILE = 'tests/qa_tester/test_data/phase4_seonhyo.cvs.csv'
API_LOGIN_ENDPOINT = 'http://localhost:8000/login'
API_CHAT_ENDPOINT = 'http://localhost:8000/chat'

LOGIN_USER = 'EMP-001'
LOGIN_PASS = 'pass1234'
REQUEST_DELAY = 0.5

def main():
    print(f"Reading {DATA_FILE}...")
    try:
        df = pd.read_csv(DATA_FILE, encoding='utf-8')
    except:
        df = pd.read_csv(DATA_FILE, encoding='cp949')
    
    # We already processed 55 items of Phase 4
    df_remaining = df.iloc[55:]
    print(f"Total remaining to test: {len(df_remaining)}")

    session = requests.Session()
    print("Logging in...")
    login_data = {"username": LOGIN_USER, "password": LOGIN_PASS}
    resp = session.post(API_LOGIN_ENDPOINT, data=login_data)
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        print("Login successful.")
    else:
        print("Login failed:", resp.text)
        return

    success_count = 0
    fail_count = 0

    for idx, row in df_remaining.iterrows():
        prompt_text = str(row['original_prompt']).strip()
        if not prompt_text or prompt_text == 'nan':
            continue

        payload = {"prompt": prompt_text}
        try:
            res = session.post(API_CHAT_ENDPOINT, json=payload, timeout=30)
            if res.status_code in [200, 403]:
                success_count += 1
                status_str = "BLOCKED" if res.status_code == 403 else "ALLOWED/MASKED"
                print(f"[{idx+1}/{len(df)}] {status_str}: {prompt_text[:30]}...")
            else:
                fail_count += 1
                print(f"[{idx+1}/{len(df)}] ERROR {res.status_code}: {res.text}")
        except Exception as e:
            fail_count += 1
            print(f"[{idx+1}/{len(df)}] EXCEPTION: {e}")
        
        time.sleep(REQUEST_DELAY)

    print(f"\nDone! Success: {success_count}, Fail: {fail_count}")

if __name__ == "__main__":
    main()
