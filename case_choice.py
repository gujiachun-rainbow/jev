"""电商售后分类。

运行：.venv/bin/python case_choice.py
学习顺序：build_case 定义输入和问题 → main 调用 API → interpret 解释答案。
"""

import json
import sys
from time import perf_counter

from typesafe_sdk import Choice, TypeSafeError

from runtime import create_client


def build_case():
    """定义待分析内容与问题；修改 state 可以尝试自己的输入。"""
    return {
        "title": "电商售后分类",
        "state": "我买的是黑色耳机，收到的却是白色，请换成黑色，暂时不用退款。",
        "questions": {
            # 多个无序选项用 Choice；other 为不匹配的输入提供出口。
            "topic": Choice(instructions="这次售后主要是什么问题？", criteria={
                "wrong_item": "商品型号、颜色或规格与订单不符",
                "delivery": "物流延误或未收到包裹",
                "payment": "扣款或账单问题", "other": "其他问题",
            }),
            "resolution": Choice(instructions="客户希望如何解决？", criteria={
                "exchange": "换成正确的商品", "refund": "退还货款",
                "information": "仅咨询信息", "unclear": "没有明确表达",
            }),
        },
    }


def interpret(result):
    """读取本案例的结构化答案，只输出建议，不执行实际业务操作。"""
    answer = result.choices["topic"]
    # confidence 描述分布集中程度，不是正确率保证；阈值仅用于演示。
    return "建议人工复核分类" if answer.confidence < 0.5 else f"建议分类：{answer.choice}"


def main():
    data = build_case()
    try:
        # 自动读取项目中的 .env，计时只围绕这一次 API 调用。
        with create_client() as client:
            start = perf_counter()
            try:
                result = client.system_one(state=data["state"], questions=data["questions"])
            finally:
                # 即使请求失败也打印耗时，单位为毫秒。
                print(f"API 调用耗时：{(perf_counter() - start) * 1000:.2f} ms", file=sys.stderr)
    except (TypeSafeError, ValueError) as error:
        print(f"案例运行失败：{type(error).__name__}，请检查配置或网络。", file=sys.stderr)
        return 1

    # 先查看完整答案，再看如何用 Python 将答案转成业务建议。
    print(f"【{data['title']}】")
    print(json.dumps(result.raw_http_response.json()["answers"], ensure_ascii=False, indent=2))
    print(interpret(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
