"""全局配置：环境变量统一从这里读"""
import os


class Settings:
    # LLM（DeepSeek，OpenAI 兼容协议）
    api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    model: str = os.getenv("LLM_MODEL", "deepseek-chat")

    # 服务地址
    frontend_url: str = os.getenv("FRONTEND_URL", "http://127.0.0.1:3000")
    # CORS：本机开发 + Docker compose 内部前端
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3080",
        "http://127.0.0.1:3080",
    ]


settings = Settings()
