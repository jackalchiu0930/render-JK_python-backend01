import os
import json
import random
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from pywebpush import webpush, WebPushException
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import uvicorn

# ===================== 環境配置 =====================
PORT = int(os.getenv("PORT", 8000))
DEFAULT_IMAGE_PATH = os.getenv("DEFAULT_IMAGE_PATH", "Icon_Jackal.png")

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "BI8v9P1eO8S_Z3uS7G6X5V4C3B2N1M0L_K9J8H7G6F5D4S3A2P1O0I9U8Y7T6R5E4W")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "mA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p")

app = FastAPI(title="Jackal AIoT Final", version="1.0.8")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== 路徑設定 =====================
BASE_DIR = Path(__file__).parent.resolve()
FRONTEND_DIR = BASE_DIR.parent / "pwa_front01-main"

ALERT_FILE = BASE_DIR / "alerts.json"
SUBS_FILE = BASE_DIR / "subscriptions.json"
CONFIG_FILE = BASE_DIR / "config.json"
UPLOAD_DIR = BASE_DIR / "Upload"
IMAGE_PATH = BASE_DIR / DEFAULT_IMAGE_PATH

UPLOAD_DIR.mkdir(exist_ok=True)
CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

VAPID_CLAIMS = {"sub": "mailto:jackal.chiualex@outlook.com"}

print(f"--- 後端目錄: {BASE_DIR} ---")
print(f"--- 前端目錄: {FRONTEND_DIR} ---")

# ===================== 數據模型 =====================
class UserData(BaseModel):
    note: str

class ConfigData(BaseModel):
    checked: bool

class CheckInRequest(BaseModel):
    employee_id: str

class CheckInResponse(BaseModel):
    success: bool
    message: str
    timestamp: str = None

# ===================== API 路由 =====================
@app.get("/")
async def root():
    starting_file = FRONTEND_DIR / "Starting.html"
    if starting_file.exists():
        return FileResponse(starting_file)
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"status": "ok", "version": "1.0.8"}

@app.post("/subscribe")
async def subscribe(sub: dict = Body(...)):
    print(f"--- 收到訂閱請求 ---")
    subs = []
    if SUBS_FILE.exists():
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
    if not ALERT_FILE.exists():
        return {"alerts": []}
    with open(ALERT_FILE, "r", encoding="utf-8") as f:
        try:
            return {"alerts": json.load(f)}
        except:
            return {"alerts": []}

@app.post("/list")
async def receive_data(data: UserData):
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    new_alert = {"time": now, "msg": data.note}
    
    alerts = []
    if ALERT_FILE.exists():
        with open(ALERT_FILE, "r", encoding="utf-8") as f:
            try: alerts = json.load(f)
            except: alerts = []
    alerts.append(new_alert)
    
    with open(ALERT_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)

    if SUBS_FILE.exists():
        with open(SUBS_FILE, "r") as f:
            subs = json.load(f)
            for sub in subs:
                try:
                    webpush(sub, json.dumps({"title": "AIoT警報", "body": data.note}), 
                           VAPID_PRIVATE_KEY, VAPID_CLAIMS)
                except Exception as e:
                    print(f"推送失敗: {e}")

    return random.randint(10000000, 99999999)

@app.get("/get-image")
async def get_image():
    if not IMAGE_PATH.exists():
        raise HTTPException(status_code=404, detail="圖片不存在")
    response = FileResponse(IMAGE_PATH, media_type="image/png", filename="Icon_Jackal.png")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

# Config 路由
@app.get("/config/check-checked")
async def check_checked():
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"checked": False}, f)
        return {"checked": False}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            return {"checked": config.get("checked", False)}
    except:
        return {"checked": False}

@app.post("/config/set-checked")
async def set_checked(data: ConfigData):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"checked": data.checked}, f)
        return {"status": "success", "checked": data.checked}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config/clear-checked")
async def clear_checked():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"checked": False}, f)
        return {"status": "success", "checked": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 上傳與浮水印
def add_watermark(image_path, text="Jackal.Chiu", font_size=40, opacity=80, angle=30):
    try:
        image = Image.open(image_path).convert("RGBA")
        watermark_layer = Image.new('RGBA', image.size, (50, 50, 50, 255))
        draw = ImageDraw.Draw(watermark_layer)
        try:
            font = ImageFont.truetype("msyh.ttc", font_size)
        except:
            font = ImageFont.load_default()
        
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        spacing_x = int(text_width * 1.5)
        spacing_y = int(text_height * 1.5)

        for x in range(-spacing_x, image.size[0] + spacing_x, spacing_x):
            for y in range(-spacing_y, image.size[1] + spacing_y, spacing_y):
                text_layer = Image.new('RGBA', (text_width, text_height), (255, 255, 255, 70))
                text_draw = ImageDraw.Draw(text_layer)
                text_draw.text((0, 0), text, font=font, fill=(255, 255, 255, opacity))
                rotated_text = text_layer.rotate(angle, expand=True)
                rx = x + (text_width - rotated_text.size[0]) // 2
                ry = y + (text_height - rotated_text.size[1]) // 2
                watermark_layer.paste(rotated_text, (rx, ry), rotated_text)

        combined = Image.alpha_composite(image, watermark_layer)
        rgb_image = combined.convert("RGB")
        rgb_image.save(image_path, format="PNG")
        print(f"--- 浮水印已添加到 {image_path} ---")
    except Exception as e:
        print(f"--- 添加浮水印失敗: {e} ---")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        if file.content_type and file.content_type.startswith("image/"):
            safe_filename = "Icon_Jackal00.png"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{file.filename}"

        file_path = UPLOAD_DIR / safe_filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if file.content_type and file.content_type.startswith("image/"):
            target_path = BASE_DIR / "Icon_Jackal.png"
            shutil.copy2(file_path, target_path)
            add_watermark(target_path)

        return {"status": "success", "filename": safe_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上傳失敗: {str(e)}")
    finally:
        file.file.close()

# 簽到功能
EMPLOYEES_FILE = BASE_DIR / "employees.json"

def load_employees_data():
    if not EMPLOYEES_FILE.exists():
        default_data = {
            "employees": [f"8219266{i}" for i in range(0, 10)],
            "course_name": "AIoT 智慧物聯網培訓",
            "checkin_records": []
        }
        with open(EMPLOYEES_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)
        return default_data
    with open(EMPLOYEES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_employees_data(data):
    with open(EMPLOYEES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.post("/checkin", response_model=CheckInResponse)
async def check_in(request: CheckInRequest):
    if len(request.employee_id) != 8 or not request.employee_id.isdigit():
        return CheckInResponse(success=False, message="工號格式錯誤，必須為8位數字")

    data = load_employees_data()
    if request.employee_id not in data.get("employees", []):
        return CheckInResponse(success=False, message="工號不存在或未授權")

    existing = data.get("checkin_records", [])
    for r in existing:
        if r.get("employee_id") == request.employee_id:
            return CheckInResponse(success=True, message="您已簽到過了", timestamp=r.get("timestamp"))

    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    new_record = {"employee_id": request.employee_id, "timestamp": now, "course": data.get("course_name")}
    existing.append(new_record)
    data["checkin_records"] = existing
    save_employees_data(data)

    return CheckInResponse(success=True, message="簽到成功", timestamp=now)

@app.get("/checkin/my-records")
async def get_my_checkin_records(employee_id: str = Query(...)):
    if len(employee_id) != 8 or not employee_id.isdigit():
        raise HTTPException(status_code=400, detail="工號格式錯誤")
    
    data = load_employees_data()
    my_records = [r for r in data.get("checkin_records", []) if r.get("employee_id") == employee_id]
    
    return {
        "employee_id": employee_id,
        "is_valid": employee_id in data.get("employees", []),
        "course_name": data.get("course_name", "未知課程"),
        "total_checkins": len(my_records),
        "records": my_records
    }

# ===================== 靜態檔案服務（必須放在最後） =====================
# 讓前端所有 HTML、圖片、sw.js 等都能被正確訪問
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

# ===================== 啟動 =====================
if __name__ == "__main__":
    print(f"=== Jackal AIoT Server 啟動 (v1.0.8) ===")
    print(f"=== 後端: {BASE_DIR} ===")
    print(f"=== 前端: {FRONTEND_DIR} ===")
    print(f"=== 端口: {PORT} ===")
    uvicorn.run(app, host="0.0.0.0", port=PORT)