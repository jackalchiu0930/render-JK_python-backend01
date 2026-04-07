import os
import json
import random
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import uvicorn

# ===================== 環境配置 =====================
PORT = int(os.getenv("PORT", 8000))

app = FastAPI(title="Jackal AIoT Platform", version="1.1.5")

# 允許跨域請求 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== 數據模型 (Models) =====================
class NoteData(BaseModel):
    note: str

class CheckInRequest(BaseModel):
    employee_id: str

class CheckInResponse(BaseModel):
    success: bool
    message: str
    timestamp: str = None

# ===================== 輔助函式 (Helpers) =====================
def load_employees_data():
    file_path = "employees.json"
    if not os.path.exists(file_path):
        # 如果檔案不存在，建立預設模板
        default_data = {
            "employees": ["82192660", "82192661"], 
            "course_name": "AIoT 智慧物聯網培訓", 
            "checkin_records": []
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=2, ensure_ascii=False)
        return default_data
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_employees_data(data):
    with open("employees.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ===================== API 路由區 =====================

# 1. [測試頁面專用] 處理隨機數與筆記寫入 alerts.json
@app.post("/list")
async def handle_list_request(data: NoteData):
    try:
        file_path = "alerts.json"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                alerts = json.load(f)
        else:
            alerts = []

        new_entry = {
            "time": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "msg": data.note
        }
        alerts.append(new_entry)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(alerts, f, indent=2, ensure_ascii=False)

        # 返回隨機數給前端
        return random.randint(1000, 9999)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器寫入失敗: {str(e)}")

# 2. [測試頁面專用] 處理文件上傳
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_location = f"./{file.filename}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        return {"message": f"檔案 {file.filename} 上傳成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. [簽到功能] 執行簽到
@app.post("/checkin", response_model=CheckInResponse)
async def checkin(request: CheckInRequest):
    data = load_employees_data()
    
    # 驗證工號是否存在
    if request.employee_id not in data.get("employees", []):
        return CheckInResponse(success=False, message="無效的工號")

    existing = data.get("checkin_records", [])
    
    # 檢查是否重複簽到
    for r in existing:
        if r.get("employee_id") == request.employee_id:
            return CheckInResponse(success=True, message="您已簽到過了", timestamp=r.get("timestamp"))

    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    new_record = {
        "employee_id": request.employee_id, 
        "timestamp": now, 
        "course": data.get("course_name", "AIoT 培訓")
    }
    existing.append(new_record)
    data["checkin_records"] = existing
    save_employees_data(data)

    return CheckInResponse(success=True, message="簽到成功", timestamp=now)

# 4. [查詢功能] 獲取個人簽到紀錄
@app.get("/checkin/my-records")
async def get_my_checkin_records(employee_id: str = Query(...)):
    data = load_employees_data()
    my_records = [r for r in data.get("checkin_records", []) if r.get("employee_id") == employee_id]
    
    return {
        "employee_id": employee_id,
        "is_valid": employee_id in data.get("employees", []),
        "course_name": data.get("course_name", "未知課程"),
        "total_checkins": len(my_records),
        "records": my_records
    }

# ===================== 靜態檔案服務 =====================
# 必須放在所有 API 路由之後，確保請求優先匹配 API
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
