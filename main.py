import os
import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 測試 1：根目錄
@app.get("/")
async def root():
    return {"message": "Server is LIVE", "version": "Diagnostic-001"}

# 測試 2：專門用來測試隨機數 (改用 GET，方便瀏覽器直接點)
@app.get("/debug/random")
async def get_random_test():
    num = random.randint(1000, 9999)
    return {"status": "success", "lucky_number": num}

# 測試 3：檢查環境變數 (確認 Render 配置)
@app.get("/debug/env")
async def check_env():
    return {"port_in_env": os.getenv("PORT"), "msg": "If you see this, routing is working!"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
