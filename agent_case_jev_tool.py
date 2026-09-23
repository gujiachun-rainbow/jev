"""案例二：DeepSeek Agent 把 Jev 当作工具，对商品候选项做相关性评分。

运行：.venv/bin/python agent_case_jev_tool.py
流程：用户需求 → Agent 调用工具 → Jev 批量评分 → Agent 给出推荐及理由。
"""

import argparse
import json
import sys
from time import perf_counter

from langchain.agents import create_agent
from langchain.tools import tool
from typesafe_sdk import Score

from agent_config import create_agent_model
from runtime import create_client

# 商品是虚构的教学数据；没有接入真实商城。
PRODUCTS = [
    {'id': 'P1', 'name': '轻行本', 'price': 4999, 'weight_kg': 1.2,
     'description': '适合办公、视频会议和通勤；集成显卡，不适合大型游戏'},
    {'id': 'P2', 'name': '游戏本', 'price': 5999, 'weight_kg': 2.5,
     'description': '独立显卡，适合游戏与三维设计，机身较重'},
    {'id': 'P3', 'name': '旗舰轻薄本', 'price': 8999, 'weight_kg': 1.1,
     'description': '适合移动办公，轻便且性能充足'},
]


def within_budget(max_price):
    # 数字大小用 Python 做确定性判断，不交给模型猜测。
    return [product for product in PRODUCTS if product['price'] <= max_price]


@tool
def evaluate_products(requirements: str, max_price: float) -> dict:
    """按用户明确给出的最高预算筛选演示笔记本，再用 Jev 评估用途匹配度。

    requirements: 用户的完整用途、便携性等需求，不可擅自添加偏好。
    max_price: 用户明确给出的最高预算，单位为人民币元。
    """
    print('[工具] evaluate_products：先检查预算，再调用 Jev')
    if max_price <= 0:
        return {'error': '预算必须大于零，请向用户确认'}
    candidates = within_budget(max_price)
    if not candidates:
        return {'products': [], 'note': '演示商品库中没有符合预算的商品'}
    # 每个候选商品一个 Score，所有问题合并到一次 Jev 请求。
    questions = {
        item['id']: Score(
            instructions={'question': 'candidate 与用户用途和偏好有多匹配？', 'candidate': item},
            criteria=['与核心用途或明确偏好冲突', '满足部分需求但有明显取舍', '符合核心用途和明确偏好'],
        ) for item in candidates
    }
    with create_client() as client:
        start = perf_counter()
        try:
            result = client.system_one(state={'requirements': requirements}, questions=questions)
        finally:
            print(f'工具内 Jev 评分耗时：{(perf_counter() - start) * 1000:.2f} ms')
    ranked = [{**item, 'match_score': result.scores[item['id']].score,
               'confidence': result.scores[item['id']].confidence} for item in candidates]
    ranked.sort(key=lambda item: item['match_score'], reverse=True)
    return {'source': '虚构商品库', 'score_range': '0～2', 'products': ranked}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('message', nargs='?', default='预算不超过6000元，主要办公和视频会议，经常出差，希望轻便，不玩游戏。推荐一款笔记本。')
    args = parser.parse_args()
    if not args.message.strip():
        parser.error('消息不能为空')
    agent = create_agent(
        model=create_agent_model(), tools=[evaluate_products],
        system_prompt=(
            '你是演示商品推荐助手。必须调用 evaluate_products 获取候选商品后再推荐。'
            '预算不明确时先追问；将用户的完整需求如实传给工具。'
            '只能推荐工具返回的商品，用中文解释评分与取舍，注明虚构商品。'
            '分数不是正确率；低置信度或低匹配度时应说明不确定，不能编造产品参数。'
        ),
    )
    start = perf_counter()
    try:
        result = agent.invoke({'messages': [{'role': 'user', 'content': args.message}]},
                              config={'recursion_limit': 12})
    finally:
        # 这里包含工具内 Jev 的耗时，不能把两项耗时再次相加。
        print(f'Agent 总耗时（含 Jev 工具）：{(perf_counter() - start) * 1000:.2f} ms')
    # 打印实际工具调用，便于理解 Agent 如何把参数交给 Python 函数。
    for message in result['messages']:
        for call in getattr(message, 'tool_calls', []):
            print('工具调用：', call['name'], json.dumps(call['args'], ensure_ascii=False))
    print('Agent 回复：', result['messages'][-1].content)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'运行失败：{type(error).__name__}，请检查 API 配置、额度或网络。', file=sys.stderr)
        raise SystemExit(1)
