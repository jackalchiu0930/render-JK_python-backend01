import os
import json
import random
import shutil
import asyncio
from typing import List
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from pywebpush import webpush, WebPushException

app = FastAPI(title="AIoT Backend Service")

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
subscriptions: List[dict] = []

# 讀取 PEM 私鑰（最推薦的方式）
try:
    with open("vapid_private.pem", "r", encoding="utf-8") as f:
        VAPID_PRIVATE_KEY = f.read().strip()
    print("已成功載入 vapid_private.pem")
except FileNotFoundError:
    print("警告：找不到 vapid_private.pem，請上傳私鑰 PEM 檔案")
    VAPID_PRIVATE_KEY = None  # 會導致推送失敗

VAPID_CLAIMS = {"sub": "mailto:jackal.chiualex@outlook.com"}

class UserData(BaseModel):
    name: str = "User"
    age: int = 0
    note: str

@app.get("/")
async def root():
    return {"status": "running", "subscriptions": len(subscriptions)}

@app.post("/subscribe")
async def subscribe(subscription: dict):
    if subscription not in subscriptions:
        subscriptions.append(subscription)
    return {"status": "success"}

@app.get("/list")
async def get_random_number():
    return {"number": random.randint(10000000, 99999999)}

@app.post("/list")
async def receive_data(data: UserData):
    return {"number": random.randint(10000000, 99999999)}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename}

async def send_push(sub: dict, payload: dict):
    if not VAPID_PRIVATE_KEY:
        print("錯誤：無效的 VAPID 私鑰")
        return
    try:
        webpush(
            subscription_info=sub,
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS
        )
    except WebPushException as ex:
        print(f"推送失敗: {ex}")
        if ex.response and ex.response.status_code in [404, 410]:
            if sub in subscriptions:
                subscriptions.remove(sub)

async def monitor_alerts():
    while True:
        if os.path.exists(ALERT_FILE):
            try:
                with open(ALERT_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        await asyncio.sleep(5)
                        continue
                    alerts = json.loads(content)
                
                for alert in alerts:
                    payload = {
                        "title": "AIoT 系統警報",
                        "body": f"{alert.get('time', '未知時間')}：{alert.get('msg', '無訊息')}",
                        "icon": "/Icon_Jackal.jpg"
                    }
                    await asyncio.gather(*[send_push(s, payload) for s in subscriptions])
                    await asyncio.sleep(0.8)

                # 清空警報
                with open(ALERT_FILE, "w", encoding="utf-8") as f:
                    json.dump([], f)

            except Exception as e:
                print(f"處理警報時錯誤: {e}")

        await asyncio.sleep(5)

@app.on_event("startup")
async def startup():
    asyncio.create_task(monitor_alerts())
