import os
import json
import random
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from pywebpush import webpush, WebPushException
from datetime import datetime

app = FastAPI(title="Jackal AIoT - Push Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("upload_files")
UPLOAD_DIR.mkdir(exist_ok=True)
ALERT_FILE = "alerts.json"
SUBS_FILE = "subscriptions.json"

# --- 嚴格同步的 VAPID 金鑰對 (請勿更動) ---
VAPID_PUBLIC_KEY = "BI8v9P1eO8S_Z3uS7G6X5V4C3B2N1M0L_K9J8H7G6F5D4S3A2P1O0I9U8Y7T6R5E4W"
VAPID_PRIVATE_KEY = "mA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p"
VAPID_CLAIMS = {"sub": "mailto:jackal.chiualex@outlook.com"}

class UserData(BaseModel):
    name: str = "User"
    age: int = 0
    note: str

@app.get("/")
async def root():
    return {"status": "AIoT Backend 運行中 (Push Ready)"}

@app.post("/subscribe")
async def subscribe(sub: dict = Body(...)):
    subs = []
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, "r") as f:
            try: subs = json.load(f)
            except: subs = []
    if sub not in subs:
        subs.append(sub)
        with open(SUBS_FILE, "w") as f:
            json.dump(subs, f)
    return {"status": "success"}

@app.get("/alerts")
async def get_alerts():
    if not os.path.exists(ALERT_FILE): return {"alerts": []}
    with open(ALERT_FILE, "r", encoding="utf-8") as f:
        try: return {"alerts": json.load(f)}
        except: return {"alerts": []}

@app.get("/list")
async def get_random_number():
    return random.randint(10000000, 99999999)

@app.post("/list")
async def receive_data(data: UserData):
    # 1. 存入 JSON (原本的功能)
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    new_alert = {"time": now, "msg": data.note}
    alerts = []
    if os.path.exists(ALERT_FILE):
        with open(ALERT_FILE, "r", encoding="utf-8") as f:
            try: alerts = json.load(f)
            except: alerts = []
    alerts.append(new_alert)
    with open(ALERT_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)

    # 2. 觸發推播 (修正點：使用 JSON 結構發送內容)
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, "r") as f:
            try:
                subs = json.load(f)
                push_data = json.dumps({
                    "title": "Jackal AIoT 警報",
                    "body": data.note
                })
                for sub in subs:
                    try:
                        webpush(
                            subscription_info=sub,
                            data=push_data,
                            vapid_private_key=VAPID_PRIVATE_KEY,
                            vapid_claims=VAPID_CLAIMS
                        )
                    except WebPushException as ex:
                        print(f"推送失敗: {ex}")
            except: pass
    
    return random.randint(10000000, 99999999)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename}
