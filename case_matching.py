"""结构化商品记录匹配。

运行：.venv/bin/python case_matching.py
学习顺序：build_case 定义输入和问题 → main 调用 API → interpret 解释答案。
"""

import json
import sys
from time import perf_counter

from typesafe_sdk import Noul, TypeSafeError

from runtime import create_client


def build_case():
    """定义待分析内容与问题；修改 state 可以尝试自己的输入。"""
    return {
        "title": "结构化商品记录匹配",
        "state": {"product": "北辰无线鼠标 M20", "color": "黑色", "connection": "蓝牙"},
        # 动态生成问题，将已有记录放进 instructions，无需手动拼接 JSON 字符串。
        "questions": {
            f"record_{record['id']}": Noul(instructions={
                "question": "输入商品与 candidate 是否是同一型号、颜色和连接方式的商品？",
                "candidate": record,
            }) for record in [
                {"id": "A", "name": "北辰 M20 蓝牙鼠标", "color": "黑色"},
                {"id": "B", "name": "北辰 M20 蓝牙鼠标", "color": "白色"},
                {"id": "C", "name": "北辰 M30 有线鼠标", "color": "黑色"},
            ]
        },
    }


def interpret(result):
    """读取本案例的结构化答案，只输出建议，不执行实际业务操作。"""
    matches = [key for key, answer in result.nouls.items() if answer.noul >= 0.8]
    return f"待人工确认的候选匹配：{matches}"


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
