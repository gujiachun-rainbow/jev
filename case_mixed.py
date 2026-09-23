"""多类型联合分诊。

运行：.venv/bin/python case_mixed.py
学习顺序：build_case 定义输入和问题 → main 调用 API → interpret 解释答案。
"""

import json
import sys
from time import perf_counter

from typesafe_sdk import Choice, Noul, Score, TypeSafeError

from runtime import create_client


def build_case():
    """定义待分析内容与问题；修改 state 可以尝试自己的输入。"""
    return {
        "title": "多类型联合分诊",
        "state": "支付接口从今天上午开始持续返回 500，所有订单都付不了款。请立即安排人工协助。",
        "questions": {
            "team": Choice(instructions="应该由哪个团队处理根本问题？", criteria={
                "engineering": "接口或系统故障", "billing": "账单金额或扣款争议", "other": "其他问题",
            }),
            "severity": Score(instructions="故障影响程度如何？", criteria=[
                "不影响正常业务", "部分业务受影响但有替代方案", "核心业务全部阻塞",
            ]),
            "human": Noul(instructions="是否明确要求人工协助？"),
        },
    }


def interpret(result):
    """读取本案例的结构化答案，只输出建议，不执行实际业务操作。"""
    urgent = (result.choices["team"].choice == "engineering"
              and result.choices["team"].confidence >= 0.5
              and result.scores["severity"].score >= 1.5
              and result.nouls["human"].noul >= 0.8)
    return f"建议加急转技术人工：{urgent}"


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
