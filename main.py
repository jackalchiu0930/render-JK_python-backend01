import os
import random
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserData(BaseModel):
    note: str

# --- 診斷用 API ---
@app.get("/api/health")
async def health():
    return {"status": "ok", "msg": "API 路由正常工作"}

@app.post("/api/test_post")
async def test_post(data: UserData):
    return {"status": "success", "received": data.note, "random": random.randint(1000, 9999)}

# --- 靜態檔案掛載 (關鍵修正) ---
# 因為你的 HTML 在 Frontend/ 資料夾，所以這裡要指向 "Frontend"
if os.path.exists("Frontend"):
    app.mount("/", StaticFiles(directory="Frontend", html=True), name="static")
else:
    # 如果沒找到資料夾，就掛載根目錄
    app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
