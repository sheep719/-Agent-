"""开发服务器入口：python run.py（读取同目录 .env，未配置 API key 时自动进入 stub 模式）"""
from dotenv import load_dotenv

load_dotenv()

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
