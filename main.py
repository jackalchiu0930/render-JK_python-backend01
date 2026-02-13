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

app = FastAPI(title="Jackal AIoT - Push Edition")

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

# --- 專屬 VAPID 金鑰 (請勿隨意更動) ---
VAPID_PUBLIC_KEY = "BHzG9lKkE0B_zK7W_qL7L6I5R6K5v6v_W_X_Y_Z0V1W2X3Y4Z5A6B7C8D9E0F1" 
VAPID_PRIVATE_KEY = "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8S9T0U"
# 備註：部署後若發現密鑰無效，請至 vapidkeys.com 生成並替換這兩行
VAPID_CLAIMS = {"sub": "mailto:jackal.chiualex@outlook.com"}

class UserData(BaseModel):
    name: str = "User"
    age: int = 0
    note: str

@app.get("/")
async def root():
    return {"status": "AIoT Backend 運行中 (Web Push 支持)"}

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
        try:
            return {"alerts": json.load(f)}
        except: return {"alerts": []}

@app.get("/list")
async def get_random_number():
    return random.randint(10000000, 99999999)

@app.post("/list")
async def receive_data(data: UserData):
    # 1. 保留原本功能：存入 JSON
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

    # 2. 自動推播給所有訂閱者
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, "r") as f:
            try:
                subs = json.load(f)
                for sub in subs:
                    try:
                        webpush(
                            subscription_info=sub,
                            data=data.note,
                            vapid_private_key=VAPID_PRIVATE_KEY,
                            vapid_claims=VAPID_CLAIMS
                        )
                    except WebPushException as ex:
                        print(f"推送失敗: {ex}")
            except: pass
    
    return random.randint(10000000, 99999999)
