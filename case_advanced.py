"""结构化退货工单。

运行：.venv/bin/python case_advanced.py
学习顺序：build_case 定义输入和问题 → main 调用 API → interpret 解释答案。
"""

import json
import sys
from time import perf_counter

from typesafe_sdk import Choice, Noul, NoulCriteria, Score, TypeSafeError

from runtime import create_client


def build_case():
    """定义待分析内容与问题；修改 state 可以尝试自己的输入。"""
    return {
        "title": "结构化退货工单",
        # 可以直接传字典；不必先拼接成大段自然语言。
        "state": {"message": "退货已签收四天，退款还没到账，请查进度。", "order": {
            "return_received": True, "days_since_return": 4, "refund_status": "processing"}},
        "questions": {
            "topic": Choice(
                instructions={"question": "客户主要在咨询什么？", "focus": ["message", "order"]},
                criteria={
                    "policy": {"definition": "询问退货条件或规则", "exclude": "已发起退货后的进度咨询"},
                    "status": {"definition": "查询已有退货或退款的进度", "examples": ["退款到哪里了", "退货是否签收"]},
                    "other": "不属于以上类型",
                }),
            "impact": Score(instructions="退款延迟对客户产生了什么影响？", criteria=[
                {"definition": "询问进度，没有表达实际损失", "examples": ["请查进度"]},
                {"definition": "资金占用造成不便，但可暂时等待", "examples": ["影响下次购物"]},
                {"definition": "资金占用造成明确的紧急生活困难", "examples": ["无法支付必需开支"]},
            ]),
            "already_returned": Noul(
                # instructions 也可以用数组，包含独立的提示或关注点。
                instructions=["是否有证据表明商家已经收到退货？", "结合 message 与 order 判断。"],
                criteria=NoulCriteria(
                    true={"definition": "商家或物流确认已签收", "examples": ["已签收", "return_received 为 true"]},
                    false={"definition": "仅申请退货或尚在运输", "examples": ["准备寄出", "尚未签收"]},
                )),
        },
    }


def interpret(result):
    """读取本案例的结构化答案，只输出建议，不执行实际业务操作。"""
    return f"咨询主题={result.choices['topic'].choice}；已收到退货的概率={result.nouls['already_returned'].noul:.2f}"


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
