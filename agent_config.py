"""只共用 DeepSeek 配置；Agent 流程和耗时打印都在各自案例里。"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek


def create_agent_model():
    load_dotenv(Path(__file__).with_name('.env'))
    key = os.getenv('DEEPSEEK_API_KEY', '').strip()
    if not key:
        raise ValueError('请在 .env 中配置 DEEPSEEK_API_KEY')
    return ChatDeepSeek(
        api_key=key,
        api_base='https://api.deepseek.com',
        model=os.getenv('DEEPSEEK_MODEL', 'deepseek-v4-flash'),
        # 入门案例关闭思考模式，直接观察工具调用过程。
        extra_body={'thinking': {'type': 'disabled'}},
        temperature=0,
        max_tokens=1200,
        timeout=60,
        max_retries=0,
    )
