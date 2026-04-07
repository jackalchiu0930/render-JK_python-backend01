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

# ===================== 環境配置 =====================
PORT = int(os.getenv("PORT", 8000))

app = FastAPI(title="Jackal AIoT Final", version="1.1.7")

# 允許跨域請求 (確保手機端連線順暢)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 數據模型 ---
class NoteData(BaseModel):
    note: str

# ===================== API 路由區 (必須放在靜態檔案之前) =====================

# [重要] 測試頁面 - 處理數據寫入與隨機數回傳
@app.post("/list")
async def handle_list_post(data: NoteData):
    try:
        file_path = "alerts.json"
        alerts = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    alerts = json.load(f)
                except:
                    alerts = []

        new_entry = {
            "time": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "msg": data.note
        }
        alerts.append(new_entry)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(alerts, f, indent=2, ensure_ascii=False)

        # 返回一個隨機數供前端顯示
        return random.randint(1000, 9999)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

# 防止 405 錯誤：支援 GET 方式訪問 /list (方便瀏覽器測試)
@app.get("/list")
async def handle_list_get():
    return {"status": "online", "message": "API is working, please use POST to submit data."}

# [重要] 處理文件上傳
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_location = f"./{file.filename}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        return {"message": f"檔案 {file.filename} 上傳成功"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

# [重要] 簽到功能 API
@app.post("/checkin")
async def checkin(employee_id: str = Body(..., embed=True)):
    # 這裡可以保留你原有的 employees.json 處理邏輯
    return {"success": True, "message": "簽到連線正常", "id": employee_id}

@app.get("/checkin/my-records")
async def get_my_records(employee_id: str = Query(...)):
    # 這裡放原有的查詢邏輯
    return {"employee_id": employee_id, "records": []}

# ===================== 靜態檔案服務 (最後防線) =====================

# 確保 index.html 存在，防止啟動報錯
if not os.path.exists("index.html"):
    with open("index.html", "w", encoding="utf-8") as f:
        f.write("<html><body><h1>Jackal AIoT Server is Running</h1></body></html>")

# 這一行必須在所有 @app.post 和 @app.get 之後
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
