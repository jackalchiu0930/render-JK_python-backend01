import os
import random
from fastapi import FastAPI
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

# --- API 路由區 ---
@app.get("/api/health")
async def health():
    return {"status": "ok", "source": "FastAPI backend"}

@app.post("/api/test_post")
async def test_post(data: UserData):
    return {"status": "success", "random": random.randint(1000, 9999)}

# --- 靜態檔案掛載 ---
# 既然你的 HTML 在 Frontend 資料夾內
# 我們把根路徑直接映射到該資料夾
app.mount("/", StaticFiles(directory="Frontend", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
