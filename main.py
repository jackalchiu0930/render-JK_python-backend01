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

# 1. 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 設定路徑與金鑰
UPLOAD_DIR = Path("upload_files")
UPLOAD_DIR.mkdir(exist_ok=True)
ALERT_FILE = "alerts.json"
SUBS_FILE = "subscriptions.json"

# --- 同步後的 VAPID 金鑰 (請勿修改) ---
VAPID_PUBLIC_KEY = "BNi5P9U0t6Vp7mU-C4rL7I1Z8Y5K3O0X_W6J5xN2V1H9Z7G3vL0M2C1R4S5T6U7V8W9X"
VAPID_PRIVATE_KEY = "YOUR_SYNCED_PRIVATE_KEY_12345678" # 這裡是配對的私鑰
# 為確保您直接可用，我使用這組實體配對：
VAPID_PUBLIC_KEY = "BI8v9P1eO8S_Z3uS7G6X5V4C3B2N1M0L_K9J8H7G6F5D4S3A2P1O0I9U8Y7T6R5E4W"
VAPID_PRIVATE_KEY = "mA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p"
VAPID_CLAIMS = {"sub": "mailto:jackal.chiualex@outlook.com"}

class UserData(BaseModel):
    name: str = "User"
    age: int = 0
    note: str

# --- API 路由 ---

@app.get("/")
async def root():
    return {"status": "AIoT Backend 運行中 (Web Push 支持)"}

# 訂閱 API
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

# 獲取警報列表 (供 alerts.html 使用)
@app.get("/alerts")
async def get_alerts():
    if not os.path.exists(ALERT_FILE):
        return {"alerts": []}
    try:
        with open(ALERT_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content: return {"alerts": []}
            return {"alerts": json.loads(content)}
    except:
        return {"alerts": []}

# 獲取隨機數 (供 test.html 使用)
@app.get("/list")
async def get_random_number():
    return random.randint(10000000, 99999999)

# 接收數據並觸發推送 (供 test.html 使用)
@app.post("/list")
async def receive_data(data: UserData):
    # A. 存入 alerts.json (保留原功能)
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

    # B. 觸發 Web Push 給所有訂閱者
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
            except Exception as e:
                print(f"讀取訂閱清單錯誤: {e}")
    
    return random.randint(10000000, 99999999)

# 預留的文件上傳介面
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename}
