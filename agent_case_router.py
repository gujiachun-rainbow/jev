"""案例一：Jev 识别诉求 → Python 分流 → 专业 Agent 查询工具并回答。

运行：.venv/bin/python agent_case_router.py
也可传入消息：.venv/bin/python agent_case_router.py '订单 DEMO-1001 到哪里了？'
"""

import argparse
import json
import sys
from time import perf_counter

from langchain.agents import create_agent
from langchain.tools import tool
from typesafe_sdk import Choice

from agent_config import create_agent_model
from runtime import create_client


@tool
def lookup_order(order_id: str) -> dict:
    """查询演示订单的物流状态，需要完整订单号，例如 DEMO-1001。"""
    print(f'[工具] lookup_order({order_id})')
    # 学习时用本地数据；生产中换成经过身份和订单归属校验的业务接口。
    orders = {'DEMO-1001': {'status': '运输中', 'latest_event': '已到达上海分拨中心'}}
    return orders.get(order_id, {'error': '未找到该演示订单，请核对订单号'})


@tool
def lookup_return_policy() -> dict:
    """查询演示店铺的售后规则，不提交申请，也不执行退款。"""
    print('[工具] lookup_return_policy()')
    return {'source': '演示规则', 'policy': '收到商品后七天内可申请退货，需核验订单及商品状态。',
            'required': ['订单号', '收货日期', '商品状态', '退货原因']}


def select_route(answer, min_confidence=0.5):
    # 不确定时返回澄清分支；置信度阈值只是教学值。
    if not 0 <= min_confidence <= 1:
        raise ValueError('置信度阈值必须在 0～1 之间')
    if answer.confidence < min_confidence or answer.choice not in {'logistics', 'aftersales'}:
        return 'clarify'
    return answer.choice


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('message', nargs='?', default='订单 DEMO-1001 到哪里了？请帮我查一下物流。')
    parser.add_argument('--min-confidence', type=float, default=0.5, help='分流置信度阈值，默认 0.5')
    args = parser.parse_args()
    if not 0 <= args.min_confidence <= 1:
        parser.error('置信度阈值必须在 0～1 之间')
    if not args.message.strip():
        parser.error('消息不能为空')

    # 1. Jev 做固定分类，不负责生成客服回复。
    with create_client() as client:
        start = perf_counter()
        try:
            decision = client.system_one(state=args.message, questions={
                'intent': Choice(instructions='用户当前最主要的诉求是什么？', criteria={
                    'logistics': '查询订单配送或物流状态',
                    'aftersales': '退货、退款、换货的规则或申请咨询',
                    'unclear': '不属于上述类别、无法确定，或同时存在多个同等重要的诉求',
                }),
            })
        finally:
            print(f'Jev 分类耗时：{(perf_counter() - start) * 1000:.2f} ms')
    answer = decision.choices['intent']
    route = select_route(answer, args.min_confidence)
    print('类别概率：', json.dumps(answer.probabilities, ensure_ascii=False))
    print(f'分流置信度阈值：{args.min_confidence:.2f}（不是所选类别的概率阈值）')
    print(f'分类：{answer.choice}，置信度：{answer.confidence:.2f}，处理分支：{route}')
    if route == 'clarify':
        print('请说明你主要想查询物流，还是咨询售后？')
        return

    # 2. 程序决定允许这个 Agent 使用哪些工具。
    # LangChain 的 create_agent 自动完成“模型 → 工具 → 模型”的循环。
    if route == 'logistics':
        tools = [lookup_order]
        role = '你是物流客服。回答订单状态前必须调用 lookup_order。缺少订单号时先追问。'
    else:
        tools = [lookup_return_policy]
        role = '你是售后客服。必须先调用 lookup_return_policy，缺少材料时追问。'
    agent = create_agent(
        model=create_agent_model(), tools=tools,
        system_prompt=role + '只依据工具数据用中文简短回答，注明是演示数据，不编造查询结果或声称完成退款。',
    )
    start = perf_counter()
    try:
        result = agent.invoke({'messages': [{'role': 'user', 'content': args.message}]},
                              config={'recursion_limit': 12})
    finally:
        print(f'Agent 执行耗时（含工具）：{(perf_counter() - start) * 1000:.2f} ms')
    print('Agent 回复：', result['messages'][-1].content)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'运行失败：{type(error).__name__}，请检查 API 配置、额度或网络。', file=sys.stderr)
        raise SystemExit(1)
