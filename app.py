import sqlite3, os, smtplib
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from email.mime.text import MIMEText
import uvicorn

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "records.db"
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "changeme")

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_name TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        battery TEXT,
        location TEXT,
        device TEXT,
        weather TEXT,
        brightness TEXT,
        volume TEXT,
        steps TEXT)""")
    try:
        conn.execute("ALTER TABLE records ADD COLUMN steps TEXT")
    except:
        pass
    conn.commit()
    conn.close()

init_db()

app = FastAPI(title="查岗系统")
app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ReportBody(BaseModel):
    app_name: str
    event: Optional[str] = None
    battery: Optional[str] = None
    location: Optional[str] = None
    device: Optional[str] = None
    weather: Optional[str] = None
    brightness: Optional[str] = None
    volume: Optional[str] = None
    steps: Optional[str] = None

class EmailBody(BaseModel):
    subject: str
    body: Optional[str] = ""

@app.post("/report")
async def report(body: ReportBody, req: Request):
    auth = req.headers.get("Authorization", "")
    if auth != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(401, "Unauthorized")
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "INSERT INTO records VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (body.app_name, now, body.battery, body.location,
         body.device, body.weather, body.brightness, body.volume, body.steps))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/ping")
async def ping():
    return "pong"

@app.post("/reset")
async def reset(req: Request):
    auth = req.headers.get("Authorization", "")
    if auth != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(401, "Unauthorized")
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("DELETE FROM records")
    conn.commit()
    conn.close()
    return {"status": "reset ok"}

@app.get("/activity/summary")
async def summary():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT app_name, timestamp, battery, location, device, weather, brightness, volume, steps FROM records ORDER BY timestamp DESC LIMIT 20"
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            "app_name": r[0],
            "timestamp": r[1],
            "battery": r[2],
            "location": r[3],
            "device": r[4],
            "weather": r[5],
            "brightness": r[6],
            "volume": r[7],
            "steps": r[8]
        })
    return {"records": result}

@app.post("/send_email")
async def send_email(data: EmailBody, req: Request):
    auth = req.headers.get("Authorization", "")
    if auth != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(401, "Unauthorized")
    try:
        msg = MIMEText(data.body, "plain", "utf-8")
        msg["Subject"] = data.subject
        msg["From"] = "jinyanling182@outlook.com"
        msg["To"] = "19217257889@163.com"
        email_password = os.environ.get("EMAIL_PASSWORD", "")
        with smtplib.SMTP("smtp.office365.com", 587) as server:
            server.starttls()
            server.login("jinyanling182@outlook.com", email_password)
            server.sendmail("jinyanling182@outlook.com", ["19217257889@163.com"], msg.as_string())
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

