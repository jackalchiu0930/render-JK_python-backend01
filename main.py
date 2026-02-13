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

app = FastAPI(title="Jackal AIoT Final")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALERT_FILE = "alerts.json"
SUBS_FILE = "subscriptions.json"

# --- 嚴格匹配金鑰 ---
VAPID_PUBLIC_KEY = "BI8v9P1eO8S_Z3uS7G6X5V4C3B2N1M0L_K9J8H7G6F5D4S3A2P1O0I9U8Y7T6R5E4W"
VAPID_PRIVATE_KEY = "mA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p"
VAPID_CLAIMS = {"sub": "mailto:jackal.chiualex@outlook.com"}

class UserData(BaseModel):
    note: str

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/subscribe")
async def subscribe(sub: dict = Body(...)):
    print(f"--- 收到訂閱請求: {sub.get('endpoint')[:30]}... ---")
    subs = []
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, "r") as f:
            try: subs = json.load(f)
            except: subs = []
    if sub not in subs:
        subs.append(sub)
        with open(SUBS_FILE, "w") as f:
            json.dump(subs, f)
    print(f"--- 目前訂閱總數: {len(subs)} ---")
    return {"status": "success"}

@app.get("/alerts")
async def get_alerts():
    if not os.path.exists(ALERT_FILE): return {"alerts": []}
    with open(ALERT_FILE, "r", encoding="utf-8") as f:
        try: return {"alerts": json.load(f)}
        except: return {"alerts": []}

@app.post("/list")
async def receive_data(data: UserData):
    # 存檔
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

    # 推送
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, "r") as f:
            subs = json.load(f)
            print(f"--- 開始推送給 {len(subs)} 個用戶 ---")
            for sub in subs:
                try:
                    webpush(sub, json.dumps({"title":"AIoT警報", "body":data.note}), VAPID_PRIVATE_KEY, VAPID_CLAIMS)
                    print("--- 推送成功發送 ---")
                except Exception as e:
                    print(f"--- 推送單一失敗: {e} ---")
    
    # 修改：回傳 8 位隨機數字
    return random.randint(10000000, 99999999)
