import os
import json
import random
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

# --- VAPID 金鑰 (請確保與前端 index.html 的 VAPID_PUB_KEY 匹配) ---
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
    
    # 避免重複訂閱
    if not any(s['endpoint'] == sub['endpoint'] for s in subs):
        subs.append(sub)
        with open(SUBS_FILE, "w") as f:
            json.dump(subs, f)
    
    print(f"--- 目前訂閱總數: {len(subs)} ---")
    return {"status": "success"}

@app.post("/list")
async def receive_data(data: UserData):
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    new_alert = {"time": now, "msg": data.note}
    
    # 存檔邏輯
    alerts = []
    if os.path.exists(ALERT_FILE):
        with open(ALERT_FILE, "r", encoding="utf-8") as f:
            try: alerts = json.load(f)
            except: alerts = []
    alerts.append(new_alert)
    with open(ALERT_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)

    # --- 依照教學構建推送內容 ---
    push_payload = {
        "title": "Jackal AIoT 警報",
        "body": data.note,
        "icon": "./Icon_Jackal.jpg"
    }

    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, "r") as f:
            subs = json.load(f)
            print(f"--- 開始推送給 {len(subs)} 個用戶 ---")
            for sub in subs:
                try:
                    webpush(
                        subscription_info=sub,
                        data=json.dumps(push_payload),
                        private_key=VAPID_PRIVATE_KEY,
                        vapid_claims=VAPID_CLAIMS
                    )
                    print("--- 推送成功 ---")
                except WebPushException as ex:
                    print(f"--- 推送失敗: {ex} ---")
                except Exception as e:
                    print(f"--- 其他錯誤: {e} ---")
                    
    return random.randint(1000, 9999)

@app.get("/alerts")
async def get_alerts():
    if not os.path.exists(ALERT_FILE): return {"alerts": []}
    with open(ALERT_FILE, "r", encoding="utf-8") as f:
        try: return {"alerts": json.load(f)}
        except: return {"alerts": []}
