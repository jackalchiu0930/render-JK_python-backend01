import os
import json
import random
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from pywebpush import webpush, WebPushException
from datetime import datetime
# 新增導入：用於返回圖片響應
from fastapi.responses import FileResponse
from fastapi import HTTPException
# 新增圖片處理相關導入
from PIL import Image, ImageDraw, ImageFont
import io
# 新增導入 uvicorn 用於本機運行
import uvicorn

# ===================== 環境變量配置 (核心：本地/Render自動适配) =====================
# 後端端口：本地默認8000，Render會自動分配端口，通過環境變量PORT獲取
PORT = int(os.getenv("PORT", 8000))
# 圖片默認路徑：本地用相對路徑，Render用環境變量指定（也可直接用相對路徑）
DEFAULT_IMAGE_PATH = os.getenv("DEFAULT_IMAGE_PATH", "Icon_Jackal.png")
# VAPID密鑰：可通過環境變量配置，避免硬編碼（本地用默認，Render可單獨配置）
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "BI8v9P1eO8S_Z3uS7G6X5V4C3B2N1M0L_K9J8H7G6F5D4S3A2P1O0I9U8Y7T6R5E4W")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "mA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p")

app = FastAPI(title="Jackal AIoT Final")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
ALERT_FILE = "alerts.json"
SUBS_FILE = "subscriptions.json"
# ========== 【修復】配置檔路徑定義 - 統一絕對路徑 (本地/Render通用) ==========
# 取得目前檔案(main.py)所在目錄，確保所有文件在項目根目錄，本地/Render一致
BASE_DIR = Path(__file__).parent.resolve()  # resolve() 轉為絕對路徑
CONFIG_FILE = BASE_DIR / "config.json"
UPLOAD_DIR = BASE_DIR / "Upload"
# 圖片路徑：統一使用項目根目錄的相對路徑，本地/Render完全一致
IMAGE_PATH = BASE_DIR / DEFAULT_IMAGE_PATH
print(f"--- 配置檔路徑: {CONFIG_FILE} ---")
print(f"--- 圖片文件路徑: {IMAGE_PATH} ---")
print(f"--- 上傳目錄路徑: {UPLOAD_DIR} ---")
print(f"--- 運行端口: {PORT} ---")

# ========== 【新增】啟動時初始化 config.json (確保文件存在) ==========
def init_config_file():
    """啟動時確保 config.json 存在，避免首次訪問時文件缺失"""
    try:
        if not CONFIG_FILE.exists():
            # 創建默認配置文件
            default_config = {"checked": False}
            # 確保目錄存在
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            # 寫入默認配置
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            print(f"--- 初始化配置檔: {CONFIG_FILE} ---")
        else:
            print(f"--- 配置檔已存在: {CONFIG_FILE} ---")
    except Exception as e:
        print(f"--- 初始化配置檔失敗: {e} ---")
# 啟動時執行初始化
init_config_file()
# 確保上傳目錄存在
UPLOAD_DIR.mkdir(exist_ok=True)

VAPID_CLAIMS = {"sub": "mailto:jackal.chiualex@outlook.com"}
class UserData(BaseModel):
    note: str
# ========== 新增：配置檔數據模型 ==========
class ConfigData(BaseModel):
    checked: bool

@app.get("/")
async def root():
    return {"status": "ok", "env": "local" if PORT == 8000 else "render", "version": "1.0.7"}

@app.post("/subscribe")
async def subscribe(sub: dict = Body(...)):
    print(f"--- 收到訂閱請求: {sub.get('endpoint')[:30]}... ---")
    subs = []
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, "r") as f:
            try: subs = json.load(f)
            except: subs = []
    if sub not in subs:
        subs.append(sub)
        with open(SUBS_FILE, "w") as f:
            json.dump(subs, f)
    print(f"--- 目前訂閱總數: {len(subs)} ---")
    return {"status": "success"}

@app.get("/alerts")
async def get_alerts():
    if not os.path.exists(ALERT_FILE): return {"alerts": []}
    with open(ALERT_FILE, "r", encoding="utf-8") as f:
        try: return {"alerts": json.load(f)}
        except: return {"alerts": []}

@app.post("/list")
async def receive_data(data: UserData):
    # 存檔
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    new_alert = {"time": now, "msg": data.note}
    alerts = []
    if os.path.exists(ALERT_FILE):
        with open(ALERT_FILE, "r", encoding="utf-8") as f:
            try: alerts = json.load(f)
            except: alerts = []
    alerts.append(new_alert)
    with open(ALERT_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)
    # 推送
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, "r") as f:
            subs = json.load(f)
            print(f"--- 開始推送給 {len(subs)} 個用戶 ---")
            for sub in subs:
                try:
                    webpush(sub, json.dumps({"title":"AIoT警報", "body":data.note}), VAPID_PRIVATE_KEY, VAPID_CLAIMS)
                    print("--- 推送成功發送 ---")
                except Exception as e:
                    print(f"--- 推送單一失敗: {e} ---")

    # 修改：回傳 8 位隨機數字
    return random.randint(10000000, 99999999)

# ========== 圖片接口 (修改：使用統一的環境變量路徑，本地/Render通用) ==========
@app.get("/get-image")
async def get_image():
    # 檢查文件是否存在
    if not os.path.exists(IMAGE_PATH):
        raise HTTPException(status_code=404, detail="圖片文件不存在")

    # 返回圖片響應 (新增：添加緩存控制頭)
    response = FileResponse(
        path=IMAGE_PATH,
        media_type="image/png",
        filename="Icon_Jackal.png"
    )
    # 新增：禁用緩存的響應頭
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ========== 【修復】配置檔管理接口 - 添加詳細日誌 (原邏輯完全保留) ==========
@app.get("/config/check-checked")
async def check_checked():
    """
    檢查是否已執行過後端檢測
    返回: {"checked": true/false}
    """
    print(f"--- 【API】收到 check-checked 請求 ---")
    print(f"--- 【API】查找配置檔: {CONFIG_FILE} ---")
    print(f"--- 【API】配置檔是否存在: {os.path.exists(CONFIG_FILE)} ---")

    if not os.path.exists(CONFIG_FILE):
        print("--- 【API】配置檔不存在，強制創建並返回 checked=False ---")
        # 【新增】若文件不存在，立即創建並返回默認值
        default_config = {"checked": False}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        return {"checked": False}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            checked_value = config.get("checked", False)
            print(f"--- 【API】讀取配置檔內容: {config} ---")
            print(f"--- 【API】返回 checked={checked_value} ---")
            return {"checked": checked_value}
    except Exception as e:
        print(f"--- 【API】讀取配置檔失敗: {e} ---")
        # 【新增】讀取失敗時，重置配置檔並返回 False
        default_config = {"checked": False}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        return {"checked": False}

@app.post("/config/set-checked")
async def set_checked(data: ConfigData):
    """
    設置檢測完成標記
    接收: {"checked": true}
    """
    print(f"--- 【API】收到 set-checked 請求: {data} ---")
    print(f"--- 【API】將寫入配置檔: {CONFIG_FILE} ---")

    try:
        config = {}
        # 如果配置檔已存在，先讀取原有內容
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                try:
                    config = json.load(f)
                    print(f"--- 【API】原有配置內容: {config} ---")
                except:
                    config = {}
                    print("--- 【API】原有配置檔損壞，重新創建 ---")
        else:
            print("--- 【API】配置檔不存在，即將創建 ---")

        # 更新標記
        config["checked"] = data.checked

        # 【關鍵】確保目錄存在（雖然 BASE_DIR 應該存在，但以防萬一）
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

        # 寫入配置檔
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"--- 【API】配置檔寫入成功: {config} ---")
        print(f"--- 【API】文件絕對路徑: {CONFIG_FILE.absolute()} ---")
        return {"status": "success", "checked": data.checked}

    except Exception as e:
        print(f"--- 【API】寫入配置檔失敗: {e} ---")
        raise HTTPException(status_code=500, detail=f"配置檔寫入失敗: {str(e)}")

@app.post("/config/clear-checked")
async def clear_checked():
    """
    清除檢測標記（用於PWA重新啟動時調用）
    返回: {"status": "success", "checked": false}
    """
    print(f"--- 【API】收到 clear-checked 請求 ---")
    print(f"--- 【API】配置檔路徑: {CONFIG_FILE} ---")

    try:
        config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                try:
                    config = json.load(f)
                except:
                    config = {}
        else:
            print("--- 【API】配置檔不存在，即將創建 ---")

        config["checked"] = False

        # 確保目錄存在
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"--- 【API】配置檔標記已清除: {config} ---")
        return {"status": "success", "checked": False}

    except Exception as e:
        print(f"--- 【API】清除配置檔失敗: {e} ---")
        raise HTTPException(status_code=500, detail=f"配置檔清除失敗: {str(e)}")

# ========== 新增：添加浮水印的函數 (原邏輯完全保留) ==========
def add_watermark(image_path, text="Jackal.Chiu", font_size=30, opacity=128, angle=30):
    """
    給圖片添加覆蓋整個畫面的半透明旋轉文字浮水印
    :param image_path: 圖片路徑
    :param text: 浮水印文字
    :param font_size: 字體大小
    :param opacity: 透明度 (0-255, 0完全透明, 255完全不透明)
    :param angle: 文字旋轉角度
    """
    try:
        # 打開圖片
        image = Image.open(image_path).convert("RGBA")
        # 創建一個透明的圖層用於繪製水印
        watermark_layer = Image.new('RGBA', image.size, (50, 50, 50, 255))
        draw = ImageDraw.Draw(watermark_layer)

        # 設置字體（優先使用系統字體，若不存在則使用默認字體）
        try:
            # Windows 默認字體路徑示例，可根據系統調整
            font = ImageFont.truetype("msyh.ttc", font_size)
        except:
            font = ImageFont.load_default(font_size)

        # 獲取文字尺寸
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # 計算重複排列的間距（文字寬高的1.5倍，避免過於密集）
        spacing_x = int(text_width * 1.5)
        spacing_y = int(text_height * 1.5)

        # 遍歷整個圖片區域，重複繪製水印文字
        for x in range(-spacing_x, image.size[0] + spacing_x, spacing_x):
            for y in range(-spacing_y, image.size[1] + spacing_y, spacing_y):
                # 創建旋轉後的文字圖層
                text_layer = Image.new('RGBA', (text_width, text_height), (255, 255, 255, 70))
                text_draw = ImageDraw.Draw(text_layer)
                # 繪製文字到臨時圖層
                text_draw.text((0, 0), text, font=font, fill=(255, 255, 255, opacity))
                # 旋轉文字圖層
                rotated_text = text_layer.rotate(angle, expand=True)
                # 計算旋轉後的文字位置
                rx = x + (text_width - rotated_text.size[0]) // 2
                ry = y + (text_height - rotated_text.size[1]) // 2
                # 將旋轉後的文字貼到水印圖層
                watermark_layer.paste(rotated_text, (rx, ry), rotated_text)

        # 合併水印圖層和原圖
        combined = Image.alpha_composite(image, watermark_layer)
        # 轉回RGB格式並保存
        rgb_image = combined.convert("RGB")
        rgb_image.save(image_path, format="PNG")
        print(f"--- 浮水印已添加到 {image_path} ---")

    except Exception as e:
        print(f"--- 添加浮水印失敗: {e} ---")
        raise

# ========== 新增：文件上傳接口 (與前端對應，原邏輯完全保留) ==========
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # 判斷是否為圖片文件（依據 Content-Type）
        if file.content_type.startswith("image/"):
            # 固定文件名，上傳圖片時直接覆蓋
            safe_filename = "Icon_Jackal00.png"
        else:
            # 非圖片文件仍使用原時間戳命名邏輯（保留原有邏輯）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{file.filename}"

        file_path = UPLOAD_DIR / safe_filename

        # 儲存檔案（覆蓋模式，w 模式會直接覆蓋已有文件）
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 新增：如果是圖片文件，複製一份到main.py同目錄並命名為Icon_Jackal.png（強制覆蓋）
        if file.content_type.startswith("image/"):
            target_path = BASE_DIR / "Icon_Jackal.png"
            shutil.copy2(file_path, target_path)  # copy2會保留文件元數據，若要完全覆蓋也可用shutil.copy

            # 新增：給複製後的圖片添加浮水印（可調整參數：字體大小、透明度、旋轉角度）
            add_watermark(target_path, font_size=40, opacity=80, angle=30)

            print(f"--- 已將 {safe_filename} 複製並覆蓋為 {target_path} ---")

        print(f"--- 文件上傳成功: {safe_filename} ---")
        return {
            "status": "success",
            "filename": safe_filename,
            "saved_path": str(file_path)
        }

    except Exception as e:
        print(f"--- 文件上傳失敗: {e} ---")
        raise HTTPException(status_code=500, detail=f"上傳失敗: {str(e)}")
    finally:
        file.file.close()

# ========== 新增：課堂簽到功能 ==========
from typing import List
import os

EMPLOYEES_FILE = BASE_DIR / "employees.json"

class CheckInRequest(BaseModel):
    employee_id: str

class CheckInResponse(BaseModel):
    success: bool
    message: str
    timestamp: str = None

def load_employees_data():
    """加載員工數據"""
    if not EMPLOYEES_FILE.exists():
        # 創建默認員工數據
        default_data = {
            "employees": ["82192660", "82192661", "82192662"],
            "course_name": "AIoT 智慧物聯網培訓",
            "checkin_records": []
        }
        with open(EMPLOYEES_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)
        return default_data

    with open(EMPLOYEES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_employees_data(data):
    """保存員工數據"""
    with open(EMPLOYEES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.post("/checkin", response_model=CheckInResponse)
async def check_in(request: CheckInRequest):
    """
    員工簽到接口
    驗證工號是否存在，並記錄簽到時間
    """
    print(f"--- 收到簽到請求: {request.employee_id} ---")

    # 驗證工號格式（必須是8位數字）
    if not request.employee_id or len(request.employee_id) != 8 or not request.employee_id.isdigit():
        return CheckInResponse(
            success=False,
            message="工號格式錯誤，必須為8位數字"
        )

    # 加載員工數據
    data = load_employees_data()
    valid_employees = data.get("employees", [])

    # 檢查工號是否在名單中
    if request.employee_id not in valid_employees:
        print(f"--- 工號 {request.employee_id} 不在名單中 ---")
        return CheckInResponse(
            success=False,
            message="工號不存在或未授權參加本課程"
        )

    # 檢查是否已簽到（避免重複簽到）
    existing_records = data.get("checkin_records", [])
    for record in existing_records:
        if record.get("employee_id") == request.employee_id:
            # 已簽到過，但仍返回成功（允許再次簽到或提示已簽到）
            print(f"--- 工號 {request.employee_id} 重複簽到 ---")
            return CheckInResponse(
                success=True,
                message="您已簽到過了，歡迎參加課程",
                timestamp=record.get("timestamp")
            )

    # 記錄新簽到
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    new_record = {
        "employee_id": request.employee_id,
        "timestamp": now,
        "course": data.get("course_name", "未知課程")
    }
    existing_records.append(new_record)
    data["checkin_records"] = existing_records

    # 保存數據
    save_employees_data(data)

    print(f"--- 工號 {request.employee_id} 簽到成功: {now} ---")

    return CheckInResponse(
        success=True,
        message="簽到成功",
        timestamp=now
    )

@app.get("/checkin/records")
async def get_checkin_records():
    """獲取所有簽到記錄（管理員用）"""
    data = load_employees_data()
    return {
        "course_name": data.get("course_name"),
        "total_employees": len(data.get("employees", [])),
        "checked_in_count": len(data.get("checkin_records", [])),
        "records": data.get("checkin_records", [])
    }

# ========== 【新增】獲取個人簽到記錄接口 ==========
@app.get("/checkin/my-records")
async def get_my_checkin_records(employee_id: str = Query(..., description="員工工號")):
    """
    獲取指定員工的個人簽到記錄
    參數: employee_id - 8位員工工號
    """
    print(f"--- 查詢個人簽到記錄: {employee_id} ---")

    # 驗證工號格式
    if not employee_id or len(employee_id) != 8 or not employee_id.isdigit():
        raise HTTPException(status_code=400, detail="工號格式錯誤，必須為8位數字")

    # 加載數據
    data = load_employees_data()

    # 檢查工號是否有效（可選：如果不需要驗證工號有效性，可以註釋掉這段）
    valid_employees = data.get("employees", [])
    is_valid = employee_id in valid_employees

    # 過濾該員工的記錄
    all_records = data.get("checkin_records", [])
    my_records = [record for record in all_records if record.get("employee_id") == employee_id]

    print(f"--- 找到 {len(my_records)} 條記錄 ---")

    return {
        "employee_id": employee_id,
        "is_valid": is_valid,
        "course_name": data.get("course_name", "未知課程"),
        "total_checkins": len(my_records),
        "records": my_records
    }

@app.get("/checkin/employees")
async def get_employee_list():
    """獲取員工名單（調試用，生產環境應該加權限控制）"""
    data = load_employees_data()
    return {
        "employees": data.get("employees", []),
        "course_name": data.get("course_name")
    }


# ========== 本機運行啟動邏輯 (修改：使用環境變量的PORT，本地/Render通用) ==========
if __name__ == "__main__":
    # 優化：添加main判斷，讓代碼結構更規範
    # host="0.0.0.0" 允許區域網絡訪問，port使用環境變量配置
    print(f"=== 服務器啟動 ===")
    print(f"=== 工作目錄: {os.getcwd()} ===")
    print(f"=== 配置檔將保存在: {CONFIG_FILE} ===")
    uvicorn.run(app, host="0.0.0.0", port=PORT)