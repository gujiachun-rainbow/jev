"""案例共用的客户端配置：读取本地 Key 并创建客户端。"""

import os
from pathlib import Path

from dotenv import load_dotenv
from typesafe_sdk import RetryPolicy, TypeSafeClient


def create_client():
    load_dotenv(Path(__file__).with_name(".env"))
    if not os.getenv("TYPESAFE_API_KEY", "").strip():
        raise ValueError("请在 .env 中设置 TYPESAFE_API_KEY")
    return TypeSafeClient(
        base_url="https://api.typesafe.ai",
        model="jev-latest",
        # 关闭自动重试，避免一次计时混入多次请求和重试等待。
        retry=RetryPolicy(max_retries=0, timeout=60.0),
    )
