"""软件缺陷评估。

运行：.venv/bin/python case_score.py
学习顺序：build_case 定义输入和问题 → main 调用 API → interpret 解释答案。
"""

import json
import sys
from time import perf_counter

from typesafe_sdk import Score, TypeSafeError

from runtime import create_client


def build_case():
    """定义待分析内容与问题；修改 state 可以尝试自己的输入。"""
    return {
        "title": "软件缺陷评估",
        "state": "Safari 点击导出 PDF 会报错，但 Chrome 能正常导出。复现步骤：登录后进入报表，选择九月，点击导出。附件有截图和错误日志。",
        "questions": {
            # 等级按列表从 0 编号。描述具体情形，不只写“低、中、高”。
            "severity": Score(instructions="故障对功能使用的影响有多大？", criteria=[
                "只有视觉或文案问题，功能可正常使用",
                "部分功能不可用，但有可行的替代操作",
                "核心操作完全受阻，没有可用替代操作",
            ]),
            # 将两个维度拆开，不把严重程度与报告完整度混为一谈。
            "report_quality": Score(instructions="报告是否提供足够的排查信息？", criteria=[
                "只有笼统描述，没有操作步骤和环境信息",
                "描述环境或操作步骤，但缺少定位证据",
                "有明确环境、复现步骤和日志或截图证据",
            ]),
        },
    }


def interpret(result):
    """读取本案例的结构化答案，只输出建议，不执行实际业务操作。"""
    answer = result.scores["severity"]
    expected = sum(level * probability for level, probability in answer.probabilities.items())
    return f"严重程度={answer.score:.2f}；由等级概率加权计算={expected:.2f}"


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
