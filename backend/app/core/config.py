from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "招标信息管理系统"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'app.db'}"
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # 阿里云 DashScope (Qwen-Long)
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_LONG_MODEL: str = "qwen-long"
    QWEN_LONG_TIMEOUT: int = 180

    # 文件上传
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    UPLOAD_MAX_SIZE: int = 20 * 1024 * 1024
    ALLOWED_EXTENSIONS: tuple = (".pdf", ".docx", ".txt", ".jpg", ".jpeg", ".png")

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
