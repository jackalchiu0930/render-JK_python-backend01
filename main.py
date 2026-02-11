import os
import json
import random
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

app = FastAPI(title="AIoT Backend - 列表顯示版")

# 1. 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 設定路徑
UPLOAD_DIR = Path("upload_files")
UPLOAD_DIR.mkdir(exist_ok=True)
ALERT_FILE = "alerts.json"

class UserData(BaseModel):
    name: str = "User"
    age: int = 0
    note: str

# 3. API 路由

@app.get("/")
async def root():
    return {"status": "AIoT Backend 運行中 (列表版)"}

# 讓 alerts.html 獲取警報列表的關鍵介面
@app.get("/alerts")
async def get_alerts():
    if not os.path.exists(ALERT_FILE):
        return {"alerts": []}
    try:
        with open(ALERT_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {"alerts": []}
            alerts = json.loads(content)
            # 直接回傳列表內容，不清除，以便 alerts.html 隨時查看
            return {"alerts": alerts}
    except Exception as e:
        return {"alerts": [], "error": str(e)}

@app.get("/list")
async def get_random_number():
    return random.randint(10000000, 99999999)

@app.post("/list")
async def receive_data(data: UserData):
    print(f"收到數據: {data.note}")
    return random.randint(10000000, 99999999)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = UPLOAD_DIR / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"message": "文件上傳成功", "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
