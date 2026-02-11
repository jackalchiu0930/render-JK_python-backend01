import os
import random
import traceback
import mimetypes
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# 獲取當前文件夾的絕對路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "upload_files")

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get("/list")
async def get_random_id():
    return random.randint(10000000, 99999999)

class UserInfo(BaseModel):
    name: str
    age: int

@app.post("/list")
async def post_user_info(user_data: UserInfo): # 這裡改名避免與內建 list 衝突
    return random.randint(10000000, 99999999)

@app.post("/upload")
async def create_upload_file(file: UploadFile):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)
    return {"filename": file.filename, "save_path": file_path}

@app.get("/download")
async def download():
    # 預設下載 AAA.png
    file_path = os.path.join(UPLOAD_DIR, "AAA.png")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件 AAA.png 不存在")
    
    media_type, _ = mimetypes.guess_type(file_path)
    if media_type is None:
        media_type = "application/octet-stream"
    
    return FileResponse(
        path=file_path,
        filename="AAA.png",
        media_type=media_type
    )

# 移除原本報錯的 download_aaa，因為上面的 download 已經處理了