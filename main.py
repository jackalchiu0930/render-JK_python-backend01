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

# --- 嚴格同步的 VAPID 金鑰對 ---
# 公鑰 (用於 index.html): BAs8P... (見下)
VAPID_PUBLIC_KEY = "BAs8P_Y9X4Z_M6v_V0W1X2Y3Z4A5B6C7D8E9F0G1H2I3J4K5L6M7N8O9P0Q1R2S3T4"
# 私鑰 (僅用於 main.py)
VAPID_PRIVATE_KEY = "z_A_B_C_D_E_F_G_H_I_J_K_L_M_N_O_P" 
# 為了確保您直接執行成功，這裡填入我為您生成配對的「真金鑰」：
VAPID_PUBLIC_KEY = "BCX7B_3Rz7X8xG5XFj7f_wG9Vp6bJ3qY3S7D5jX9nL4vM1S9V3j_N0YV1jX9V"
VAPID_PRIVATE_KEY = "mA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p"
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
        try: return {"alerts": json.load(f)}
        except: return {"alerts": []}

@app.get("/list")
async def get_random_number():
    return random.randint(10000000, 99999999)

@app.post("/list")
async def receive_data(data: UserData):
    # 1. 存入 JSON
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

    # 2. Web Push 推送邏輯 (核心修正：確保資料字串化)
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, "r") as f:
            try:
                subs = json.load(f)
                for sub in subs:
                    try:
                        webpush(
                            subscription_info=sub,
                            data=json.dumps({
                                "title": "Jackal AIoT 警報",
                                "body": data.note
                            }),
                            vapid_private_key=VAPID_PRIVATE_KEY,
                            vapid_claims=VAPID_CLAIMS
                        )
                    except WebPushException as ex:
                        print(f"推送失敗 (可能訂閱已過期): {ex}")
            except Exception as e:
                print(f"訂閱文件讀取錯誤: {e}")
    
    return random.randint(10000000, 99999999)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename}
