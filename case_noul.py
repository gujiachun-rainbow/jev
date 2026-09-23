"""客服条件判断。

运行：.venv/bin/python case_noul.py
学习顺序：build_case 定义输入和问题 → main 调用 API → interpret 解释答案。
"""

import json
import sys
from time import perf_counter

from typesafe_sdk import Noul, NoulCriteria, TypeSafeError

from runtime import create_client


def build_case():
    """定义待分析内容与问题；修改 state 可以尝试自己的输入。"""
    return {
        "title": "客服条件判断",
        "state": "这是我第三次联系你们了，前两次都没解决。请转人工客服，我要退回这笔订阅费。",
        "questions": {
            # 每个问题只判断一个条件；多个条件的组合由 Python 完成。
            "human": Noul(instructions="客户是否明确要求人工客服？"),
            "refund": Noul(instructions="客户是否要求退款？"),
            "repeat": Noul(instructions="客户是否曾为同一个问题联系过客服？",
                criteria=NoulCriteria(
                    true="提到此前联系、已有工单或多次咨询同一个问题",
                    false="首次咨询，或没有提及此前联系",
                )),
        },
    }


def interpret(result):
    """读取本案例的结构化答案，只输出建议，不执行实际业务操作。"""
    # 0.2～0.8 作为不确定区间，真实阈值需用自己的样本验证。
    values = {key: answer.noul for key, answer in result.nouls.items()}
    if any(0.2 < value < 0.8 for value in values.values()):
        return "存在不确定条件，建议人工复核"
    return f"建议人工接待={values['human'] >= 0.8}；标记重复咨询={values['repeat'] >= 0.8}；登记退款诉求={values['refund'] >= 0.8}"


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
