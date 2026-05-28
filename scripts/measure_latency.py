import requests
import time

# Ollama 직접 호출로 응답 시간 측정
print("=== Ollama qwen2.5:7b 응답 시간 측정 ===")

# Judge call
start = time.time()
r = requests.post('http://localhost:11434/api/chat', json={
    'model': 'qwen2.5:7b',
    'messages': [
        {'role': 'system', 'content': 'You are a security system. Respond ONLY with JSON: {"intent": "SAFE"} or {"intent": "BLOCKED", "reason": "reason"}'},
        {'role': 'user', 'content': '2024년 매출 보고서를 작성해줘'}
    ],
    'stream': False,
    'format': 'json',
    'options': {'temperature': 0.0}
}, timeout=90)
judge_time = time.time() - start
content = r.json().get('message', {}).get('content', '')
print(f"Judge 응답 시간: {judge_time:.1f}s")
print(f"Judge 응답: {content[:100]}")

# GenMask call
start = time.time()
r2 = requests.post('http://localhost:11434/api/chat', json={
    'model': 'qwen2.5:7b',
    'messages': [
        {'role': 'system', 'content': 'Find confidential data. Return {"found": false} or {"found": true, "entities": []}'},
        {'role': 'user', 'content': '2024년 매출 보고서를 작성해줘'}
    ],
    'stream': False,
    'format': 'json',
    'options': {'temperature': 0.0}
}, timeout=90)
mask_time = time.time() - start
content2 = r2.json().get('message', {}).get('content', '')
print(f"GenMask 응답 시간: {mask_time:.1f}s")
print(f"GenMask 응답: {content2[:100]}")

print(f"\n총 예상 소요 시간(2회 호출): {judge_time + mask_time:.1f}s")
print(f"현재 OLLAMA_TIMEOUT=30 -> 필요 timeout: {int(judge_time + mask_time) + 10}s 이상")
