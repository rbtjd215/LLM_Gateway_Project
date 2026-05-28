"""admin_log_check.py - admin/logs DB 조회 검증"""
import urllib.request, json

BASE = "http://localhost:8000"
token = json.loads(urllib.request.urlopen(
    urllib.request.Request(
        BASE + "/login",
        data=json.dumps({"employee_num": "ADMIN-001", "password": "adminpass"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
).read())["access_token"]

resp = urllib.request.urlopen(urllib.request.Request(
    BASE + "/admin/logs",
    headers={"Authorization": f"Bearer {token}"},
    method="GET",
))
data = json.loads(resp.read())
total = data["total"]
print(f"총 {total}건 조회됨 (더미 데이터가 아닌 실제 DB 기록)")
print("-" * 70)
for log in data["logs"]:
    print(f"[{log['status']:8}] {log['timestamp']} | {log['employee_num']} | {log['detected_threat'][:55]}")
