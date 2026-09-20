import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    HOST = os.getenv("KV_HOST", "0.0.0.0")
    PORT = int(os.getenv("KV_PORT", "6379"))
    AOF_PATH = os.getenv("KV_AOF_PATH", "./data/appendonly.aof")
    COMPACT_INTERVAL = int(os.getenv("KV_COMPACT_INTERVAL", "60"))
    TTL_SWEEP_INTERVAL = int(os.getenv("KV_TTL_SWEEP_INTERVAL", "1"))
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/metadata.db")
    ADMIN_PORT = int(os.getenv("ADMIN_PORT", "8080"))