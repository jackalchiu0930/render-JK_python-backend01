import os
import random
import shutil
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

app = FastAPI(title="AIoT Backend Service")

# 1. 配置 CORS (極其重要：否則前端無法存取後端)
# 部署到 Render 後，這裡的 origins 可以保持 ["*"] 方便開發，或填入你前端的網址
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 定義文件存放路徑
UPLOAD_DIR = Path("upload_files")
UPLOAD_DIR.mkdir(exist_ok=True)

# 3. 定義文字數據的結構 (對應前端的 UserInfo)
class UserData(BaseModel):
    name: str = "User"
    age: int = 0
    note: str  # 對應前端輸入框的內容

# --- API 路由設計 ---

# 功能 2.1 & 2.3: 請求隨機 8 位數字 (Button01)
@app.get("/list")
async def get_random_number():
    # 生成 10,000,000 到 99,999,999 之間的數字
    random_num = random.randint(10000000, 99999999)
    return random_num

# 功能 2.2: 接收輸入框的數據提交 (提交按鈕)
@app.post("/list")
async def receive_data(data: UserData):
    print(f"收到數據: 姓名={data.name}, 年齡={data.age}, 備註={data.note}")
    # 這裡你可以後續串接數據庫儲存 data.note
    # 回傳一個隨機 ID 代表提交成功
    return random.randint(10000000, 99999999)

# 功能 2.1: 文件上傳 (Button02)
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # 安全地保存文件
        file_path = UPLOAD_DIR / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "message": "文件上傳成功",
            "filename": file.filename,
            "path": str(file_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上傳失敗: {str(e)}")

# 測試路由：檢查後端是否正常運作
@app.get("/")
async def root():
    return {"status": "AIoT Backend is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
