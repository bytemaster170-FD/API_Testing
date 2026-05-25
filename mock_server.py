"""
Mock server mimicking HealthRX hiring API
Deployable on Railway / Render / Fly.io
Includes a live request log dashboard at GET /
"""

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import secrets
import datetime
import json

app = FastAPI(title="HealthRX Mock API")

request_log = []
_valid_token: Optional[str] = None


def log_event(endpoint: str, direction: str, data: dict):
    request_log.insert(0, {
        "time": datetime.datetime.utcnow().strftime("%H:%M:%S UTC"),
        "endpoint": endpoint,
        "direction": direction,
        "data": data
    })
    if len(request_log) > 50:
        request_log.pop()


class GenerateRequest(BaseModel):
    name: str
    regNo: str
    email: str

class SubmitRequest(BaseModel):
    finalQuery: str


@app.get("/", response_class=HTMLResponse)
def dashboard():
    rows = ""
    for entry in request_log:
        data_str = json.dumps(entry["data"], indent=2)
        direction_color = "#4ade80" if entry["direction"] == "RESPONSE" else "#60a5fa"
        rows += f"""
        <div class="entry">
          <div class="meta">
            <span class="time">{entry['time']}</span>
            <span class="ep">{entry['endpoint']}</span>
            <span class="dir" style="color:{direction_color}">{entry['direction']}</span>
          </div>
          <pre>{data_str}</pre>
        </div>
        """

    if not rows:
        rows = "<div class='empty'>No requests yet. Run your client.py to see logs here.</div>"

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="3">
  <title>HealthRX Mock API — Live Log</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #0f172a; color: #e2e8f0; font-family: 'Courier New', monospace; padding: 24px; }}
    h1 {{ font-size: 1.4rem; color: #7dd3fc; margin-bottom: 4px; }}
    .subtitle {{ color: #64748b; font-size: 0.8rem; margin-bottom: 24px; }}
    .endpoints {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 16px 20px; margin-bottom: 24px; font-size: 0.8rem; }}
    .endpoints h2 {{ color: #7dd3fc; font-size: 0.9rem; margin-bottom: 10px; }}
    .endpoints .route {{ color: #a3e635; margin: 4px 0; }}
    .endpoints .route span {{ color: #94a3b8; }}
    .log-title {{ color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px; }}
    .entry {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px; }}
    .meta {{ display: flex; gap: 12px; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }}
    .time {{ color: #64748b; font-size: 0.75rem; }}
    .ep {{ background: #0f172a; color: #f8fafc; border-radius: 4px; padding: 2px 8px; font-size: 0.75rem; }}
    .dir {{ font-size: 0.75rem; font-weight: bold; }}
    pre {{ background: #0f172a; border-radius: 6px; padding: 10px; font-size: 0.78rem; color: #cbd5e1; overflow-x: auto; white-space: pre-wrap; word-break: break-word; }}
    .empty {{ color: #475569; font-size: 0.85rem; text-align: center; padding: 40px; }}
    .refresh-note {{ color: #334155; font-size: 0.72rem; margin-top: 16px; text-align: center; }}
  </style>
</head>
<body>
  <h1>⚡ HealthRX Mock API</h1>
  <p class="subtitle">Live request/response log — auto-refreshes every 3 seconds</p>
  <div class="endpoints">
    <h2>Available Endpoints</h2>
    <div class="route">POST <span>/hiring/generateWebhook/PYTHON</span> → returns webhook + accessToken</div>
    <div class="route">POST <span>/hiring/testWebhook/PYTHON</span> → validates token + finalQuery</div>
  </div>
  <div class="log-title">📡 Live Request Log</div>
  {rows}
  <p class="refresh-note">Auto-refreshing every 3s</p>
</body>
</html>"""


@app.post("/hiring/generateWebhook/PYTHON")
async def generate_webhook(body: GenerateRequest, request: Request):
    global _valid_token
    _valid_token = secrets.token_hex(32)
    last_digit = int(body.regNo[-1])
    question = "Q1 (odd)" if last_digit % 2 != 0 else "Q2 (even)"
    # Use forwarded scheme (Railway/Render terminate TLS externally, base_url is http://)
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    base = f"{scheme}://{host}"
    webhook_url = f"{base}/hiring/testWebhook/PYTHON"

    log_event("/generateWebhook/PYTHON", "REQUEST", {"name": body.name, "regNo": body.regNo, "email": body.email})
    resp = {"status": "success", "webhook": webhook_url, "accessToken": _valid_token, "data": {"question": question, "lastDigit": last_digit}}
    log_event("/generateWebhook/PYTHON", "RESPONSE", resp)
    return resp


@app.post("/hiring/testWebhook/PYTHON")
async def test_webhook(body: SubmitRequest, authorization: Optional[str] = Header(None)):
    log_event("/testWebhook/PYTHON", "REQUEST", {"Authorization": authorization or "MISSING", "finalQuery": body.finalQuery})

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if authorization != _valid_token:
        raise HTTPException(status_code=403, detail="Invalid or expired accessToken")
    if not body.finalQuery.strip():
        raise HTTPException(status_code=400, detail="finalQuery cannot be empty")

    resp = {"status": "success", "message": "SQL query received and validated!", "received": {"finalQuery": body.finalQuery}}
    log_event("/testWebhook/PYTHON", "RESPONSE", resp)
    return resp