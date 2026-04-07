import os
import json
import random
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
import uvicorn

# ===================== 基礎配置 =====================
PORT = int(os.getenv("PORT", 8000))
app = FastAPI(title="Jackal AIoT System", version="1.1.6")

# 允許跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 數據模型
class NoteData(BaseModel):
    note: str

class CheckInRequest(BaseModel):
    employee_id: str

# ===================== API 路由 (必須放在最前面) =====================

# 1. 測試頁面用的 API (對應 test.html)
@app.post("/list")
async def handle_list_request(data: NoteData):
    try:
        file_path = "alerts.json"
        # 讀取現有紀錄
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    alerts = json.load(f)
                except:
                    alerts = []
        else:
            alerts = []

        # 新增紀錄
        new_entry = {
            "time": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "msg": data.note
        }
        alerts.append(new_entry)

        # 存檔
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(alerts, f, indent=2, ensure_ascii=False)

        # 回傳隨機數
        return random.randint(1000, 9999)
    except Exception as e:
        print(f"Error in /list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 2. 文件上傳 API
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_location = f"./{file.filename}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        return {"message": "Success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. 簽到 API
@app.post("/checkin")
async def checkin(request: CheckInRequest):
    # 這裡可以根據你的需求補回 employees.json 的邏輯
    return {"success": True, "message": "簽到功能正常"}

# 4. 取得紀錄 API
@app.get("/checkin/my-records")
async def get_records(employee_id: str = Query(...)):
    return {"employee_id": employee_id, "records": []}

# ===================== 靜態檔案服務 (必須放在 API 之後) =====================

# 掛載當前目錄下的所有靜態檔案 (HTML, JS, CSS, JPG)
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
