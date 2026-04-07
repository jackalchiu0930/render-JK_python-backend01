import os
import json
import random
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import uvicorn

# ===================== 配置區 =====================
PORT = int(os.getenv("PORT", 8000))
ALERT_FILE = "alerts.json"

app = FastAPI(title="Jackal AIoT Platform")

# 跨域配置 (保持與成功版本一致)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定義接收格式
class UserData(BaseModel):
    note: str

# ===================== API 路由區 =====================

# 1. 核心測試介面 (處理隨機數與存檔)
@app.post("/list")
async def receive_data(data: UserData):
    try:
        # 存檔邏輯
        now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        new_alert = {"time": now, "msg": data.note}
        
        alerts = []
        if os.path.exists(ALERT_FILE):
            with open(ALERT_FILE, "r", encoding="utf-8") as f:
                try:
                    alerts = json.load(f)
                except:
                    alerts = []
        
        alerts.append(new_alert)
        with open(ALERT_FILE, "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)

        # 回傳隨機數 (讓前端顯示)
        return random.randint(1000, 9999)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. 檔案上傳介面
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_location = f"./{file.filename}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        return {"message": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. 根目錄檢查 (Render 健康檢查用)
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# ===================== 靜態檔案服務 =====================

# 重要：這段必須放在所有 @app.post 之後
# 這樣當請求 /list 時，會先被上面的 API 攔截，而不是被當作找靜態檔案
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
