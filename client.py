"""
Python client — run this after deploying mock_server.py
Change BASE_URL to your live Railway/Render URL
"""
import requests

# 👇 Change this to your deployed URL (e.g. https://your-app.up.railway.app)
BASE_URL = "http://localhost:8000"

print("=" * 55)
print("STEP 1: Calling generateWebhook...")
print("=" * 55)

payload = {
    "name": "John Doe",
    "regNo": "REG12347",
    "email": "john@example.com"
}

r1 = requests.post(f"{BASE_URL}/hiring/generateWebhook/PYTHON", json=payload)
r1.raise_for_status()
data = r1.json()
print("Response:", data)

webhook_url  = data["webhook"]
access_token = data["accessToken"]
print(f"\nWebhook : {webhook_url}")
print(f"Token   : {access_token}")

# SQL query (odd regNo → Q1)
last_digit = int(payload["regNo"][-1])
if last_digit % 2 != 0:
    final_query = """SELECT name, salary
FROM (
    SELECT name, salary,
           DENSE_RANK() OVER (ORDER BY salary DESC) AS rnk
    FROM employees
) ranked
WHERE rnk = 2;"""
else:
    final_query = """SELECT department, MAX(salary) AS highest_salary
FROM employees
GROUP BY department
ORDER BY highest_salary DESC;"""

print(f"\n{'=' * 55}")
print("STEP 2: SQL Query:")
print("=" * 55)
print(final_query)

print(f"\n{'=' * 55}")
print("STEP 3: Submitting to testWebhook...")
print("=" * 55)

r2 = requests.post(
    webhook_url,
    json={"finalQuery": final_query},
    headers={"Authorization": access_token, "Content-Type": "application/json"}
)
r2.raise_for_status()
print("Response:", r2.json())
print("\n✅ Done!")
