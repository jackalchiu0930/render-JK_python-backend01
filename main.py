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

app = FastAPI(title="Jackal AIoT Final")

# 1. 跨域配置 (必須最先載入)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALERT_FILE = "alerts.json"

class UserData(BaseModel):
    note: str

# 2. API 路由 (必須放在 StaticFiles 之前)
@app.post("/list")
async def receive_data(data: UserData):
    try:
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

        # 返回隨機數給前端
        return random.randint(1000, 9999)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_location = f"./{file.filename}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        return {"message": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. 靜態檔案掛載 (放在最後)
# 確保路徑正確，如果檔案在根目錄，使用 "."
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    # Render 會自動給 PORT，如果沒有則用 8000
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
