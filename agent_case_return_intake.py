"""第六章：Agent 收集售后咨询信息，Jev 每轮检查商品和问题是否已说明。"""

import argparse
import json
import sys

from langchain.agents import create_agent
from typesafe_sdk import Noul

from agent_config import create_agent_model
from runtime import create_client


FIELDS = {"product": "商品名称或类型", "problem": "具体问题或异常表现"}
DEMO_TURNS = [
    "我想咨询一下售后。",
    "买的是一副蓝牙耳机。",
    "左耳一直没有声音，右耳可以正常播放。",
]


def build_questions():
    # 每个条件独立检查；只依据用户陈述，不把助手的举例当作事实。
    common = "只依据用户陈述；明确更正以最新说法为准，矛盾未解决时视为未说明。"
    return {
        "product": Noul(instructions=common +
            "用户是否明确说出了咨询的商品名称或类型？如蓝牙耳机即可，"
            "不要求品牌型号；只说这个东西、刚买的商品不算。"),
        "problem": Noul(instructions=common +
            "用户是否描述了该商品可识别的具体问题或异常表现？"
            "如左耳无声、杯子有裂缝；只说坏了、不好用、想售后不算。"),
    }


def missing_information(result, threshold=0.8):
    if not 0 <= threshold <= 1:
        raise ValueError("阈值必须在 0～1 之间")
    missing = []
    for key in FIELDS:
        answer = result.nouls.get(key)
        if answer is None or not 0 <= answer.noul <= 1 or answer.noul < threshold:
            missing.append(key)
    return missing


def run_turn(client, model, user_statements, messages, threshold=0.8):
    result = client.system_one(
        state={"user_statements": list(user_statements)},
        questions=build_questions(),
    )
    missing = missing_information(result, threshold)
    print("jev->信息存在概率：", json.dumps(
        {key: answer.noul for key, answer in result.nouls.items()}, ensure_ascii=False))
    print("jev->仍需确认：", "、".join(FIELDS[key] for key in missing) or "无")
    if missing:
        instruction = "本轮只追问这一项：" + FIELDS[missing[0]] + "。用一句自然的问题，不要输出摘要。"
    else:
        instruction = (
            "信息收集完成。输出简短的售后咨询摘要，包含商品和具体问题，"
            "并说明摘要仅供后续咨询使用，尚未提交售后申请。不要再追问。"
        )
    agent = create_agent(
        model=model,
        tools=[],
        system_prompt=(
            "你是中文售后咨询助手。" + instruction +
            "仅使用用户明确提供的事实，明确更正以最新说法为准。"
            "不要把自己提问中的示例当作用户信息。"
            "不诊断原因，不承诺退款或换货，不声称已创建工单。"
        ),
    )
    response = agent.invoke({"messages": messages}, config={"recursion_limit": 6})
    reply = response["messages"][-1].content
    print("Agent：", reply)
    messages.append({"role": "assistant", "content": reply})
    return not missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interactive", action="store_true", help="改为键盘输入，输入 exit 退出")
    parser.add_argument("--threshold", type=float, default=0.8)
    args = parser.parse_args()
    if not 0 <= args.threshold <= 1:
        parser.error("阈值必须在 0～1 之间")
    messages, user_statements = [], []
    model = create_agent_model()
    with create_client() as client:
        turns = iter(DEMO_TURNS)
        while True:
            text = input("你：").strip() if args.interactive else next(turns, None)
            if text is None:
                print("预设消息已结束；若仍有缺项，可用 --interactive 继续体验新会话。")
                break
            if text.lower() == "exit":
                break
            if not text.strip():
                continue
            if not args.interactive:
                print("\n预设用户：", text)
            user_statements.append(text)
            messages.append({"role": "user", "content": text})
            if run_turn(client, model, user_statements, messages, args.threshold):
                break
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EOFError, KeyboardInterrupt):
        print("\n已结束咨询。")
    except Exception as error:
        print(f"本轮未完成：{type(error).__name__}，请检查配置或网络后重试。", file=sys.stderr)
        raise SystemExit(1)
