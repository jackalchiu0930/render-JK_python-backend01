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
subscriptions = []

class UserData(BaseModel):
    name: str = "User"
    age: int = 0
    note: str

VAPID_PRIVATE_KEY = "l-ms405jj1V4Mc0sGJz28kjaiiouZSH1YUj8CNCMUIA"
VAPID_CLAIMS = {"sub": "mailto:jackal@example.com"}

@app.get("/")
async def root():
    return {"status": "running", "subs": len(subscriptions)}

@app.post("/subscribe")
async def subscribe(subscription: dict):
    if subscription not in subscriptions:
        subscriptions.append(subscription)
    return {"status": "success"}

@app.get("/list")
async def get_random_number():
    return random.randint(10000000, 99999999)

@app.post("/list")
async def receive_data(data: UserData):
    return random.randint(10000000, 99999999)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename}

async def send_push(sub, msg):
    try:
        webpush(subscription_info=sub, data=msg, 
                vapid_private_key=VAPID_PRIVATE_KEY, vapid_claims=VAPID_CLAIMS)
    except WebPushException as ex:
        if ex.response and ex.response.status_code in [404, 410]:
            subscriptions.remove(sub)

async def monitor_alerts():
    while True:
        if os.path.exists(ALERT_FILE):
            try:
                with open(ALERT_FILE, "r+", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        alerts = json.loads(content)
                        for alert in alerts:
                            msg = f"【警報】{alert.get('time')}: {alert.get('msg')}"
                            await asyncio.gather(*[send_push(s, msg) for s in subscriptions])
                            await asyncio.sleep(1)
                        f.seek(0)
                        f.write(json.dumps([]))
                        f.truncate()
            except: pass
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup():
    asyncio.create_task(monitor_alerts())
