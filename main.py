import os
import json
import random
import shutil
import asyncio
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from pywebpush import webpush, WebPushException

app = FastAPI(title="AIoT Backend Service with Push Notification")

# --- 1. 配置 CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. 路徑與資料結構設定 ---
UPLOAD_DIR = Path("upload_files")
UPLOAD_DIR.mkdir(exist_ok=True)
ALERT_FILE = "alerts.json"

# 儲存 PWA 訂閱資訊的列表 (正式環境建議存入資料庫)
subscriptions = []

class UserData(BaseModel):
    name: str = "User"
    age: int = 0
    note: str

# --- 3. Web Push (VAPID) 配置 ---
# 請替換為您產生的金鑰。若無金鑰，建議搜尋 "VAPID generator" 線上產生
VAPID_PUBLIC_KEY = "您的公鑰 (放前端 index.html 使用)"
VAPID_PRIVATE_KEY = "您的私鑰 (嚴禁外洩)"
VAPID_CLAIMS = {
    "sub": "mailto:your-email@example.com"
}

# --- 4. API 路由設計 ---

@app.get("/")
async def root():
    return {"status": "AIoT Backend is running!", "active_subscriptions": len(subscriptions)}

# 接收前端 PWA 訂閱資訊
@app.post("/subscribe")
async def subscribe(subscription: dict):
    if subscription not in subscriptions:
        subscriptions.append(subscription)
        print(f"新用戶訂閱成功！當前總訂閱數: {len(subscriptions)}")
    return {"status": "success"}

# 原有的功能：請求隨機數字
@app.get("/list")
async def get_random_number():
    return random.randint(10000000, 99999999)

# 原有的功能：提交數據
@app.post("/list")
async def receive_data(data: UserData):
    print(f"收到數據: {data.note}")
    return random.randint(10000000, 99999999)

# 原有的功能：文件上傳
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = UPLOAD_DIR / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"message": "文件上傳成功", "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 5. 消息推送核心邏輯 ---

async def send_notification(subscription, message_text):
    """執行單一用戶的 Web Push 推送"""
    try:
        webpush(
            subscription_info=subscription,
            data=message_text,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS
        )
        return True
    except WebPushException as ex:
        print(f"推送失敗: {ex}")
        # 如果用戶已退訂或 Token 失效，可從清單移除
        if ex.response and ex.response.status_code in [404, 410]:
            subscriptions.remove(subscription)
        return False

async def monitor_alerts_task():
    """後台任務：監控 alerts.json 並逐行推送消息"""
    while True:
        try:
            if os.path.exists(ALERT_FILE):
                with open(ALERT_FILE, "r+", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        alerts = json.loads(content)
                        if alerts and isinstance(alerts, list):
                            print(f"發現 {len(alerts)} 條待推送警報...")
                            for alert in alerts:
                                # 格式化消息內容
                                msg = f"【系統警報】\n時間：{alert.get('time')}\n內容：{alert.get('msg')}"
                                
                                # 推送給所有訂閱者
                                tasks = [send_notification(sub, msg) for sub in subscriptions]
                                await asyncio.gather(*tasks)
                                
                                print(f"已推送: {alert.get('msg')}")
                                await asyncio.sleep(1) # 每一行消息間隔 1 秒
                            
                            # 推送完畢後清空 JSON 檔案
                            f.seek(0)
                            f.write(json.dumps([]))
                            f.truncate()
        except Exception as e:
            print(f"監控任務異常: {e}")
        
        await asyncio.sleep(5) # 每 5 秒檢查一次設定檔

# --- 6. 啟動後台任務 ---
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(monitor_alerts_task())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
