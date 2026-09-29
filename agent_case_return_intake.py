"""第六章：Agent 收集售后咨询信息，Jev 每轮检查商品和问题是否已说明。"""

import argparse
import json
import sys
from time import perf_counter

from langchain.agents import create_agent
from typesafe_sdk import Noul

from agent_config import create_agent_model
from runtime import create_client


# 字段顺序也是追问顺序：先确认商品，再确认具体问题。
FIELDS = {"product": "商品名称或类型", "problem": "具体问题或异常表现"}
# 默认按三轮演示；交互模式下改为读取用户的键盘输入。
DEMO_TURNS = [
    "我想咨询一下售后。",
    "买的是一副蓝牙耳机。",
    "左耳一直没有声音，右耳可以正常播放。",
]


def log(stage, message, *, core=False, error=False):
    """核心日志展示对话与结果，过程日志展示内部步骤；每行保留来源标记。"""
    # 默认是过程日志；用户需要看到的回复和提示显式标为核心，错误始终为核心。
    category = "核心" if core or error else "过程"
    for line in str(message).splitlines() or [""]:
        print(f"[{category}][{stage}] {line}", file=sys.stderr if error else sys.stdout, flush=True)


def build_questions():
    """构建两个独立的 Noul 问题，一次请求检查两项信息。"""
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
    """将概率转成待确认字段；等于门槛时通过，缺失或无效时继续追问。"""
    if not 0 <= threshold <= 1:
        raise ValueError("阈值必须在 0～1 之间")
    missing = []
    for key in FIELDS:
        answer = result.nouls.get(key)
        if answer is None or not 0 <= answer.noul <= 1 or answer.noul < threshold:
            missing.append(key)
    return missing


def run_turn(client, model, user_statements, messages, threshold=0.8):
    """完成一轮检查与回复，返回是否已进入摘要阶段。"""
    # 1. Jev 只接收用户陈述，避免助手提问中的示例被当作真实信息。
    log("Jev", f"开始检查，累计用户陈述 {len(user_statements)} 条，判断门槛 {threshold:.2f}")
    state = {"user_statements": list(user_statements)}
    questions = build_questions()
    # 打印本次实际传入的参数；问题对象转成 JSON 展示，调用仍使用原对象。
    log("Jev", "提交 state：\n" + json.dumps(state, ensure_ascii=False, indent=2))
    log("Jev", "提交 questions：\n" + json.dumps(
        {key: question.model_dump(mode="json", exclude_none=True)
         for key, question in questions.items()}, ensure_ascii=False, indent=2))
    started = perf_counter()
    try:
        result = client.system_one(
            state=state,
            questions=questions,
        )
    finally:
        # 即使请求失败，也记录此次调用耗时；耗时日志不表示请求成功。
        log("Jev", f"本次调用耗时：{perf_counter() - started:.2f} 秒")
    missing = missing_information(result, threshold)
    log("Jev", "信息存在概率：" + json.dumps(
        {key: answer.noul for key, answer in result.nouls.items()}, ensure_ascii=False))
    log("流程", "仍需确认：" + ("、".join(FIELDS[key] for key in missing) or "无"))
    # 2. 业务代码决定本轮任务，Agent 负责将任务表达成自然语言。
    if missing:
        log("流程", "进入追问阶段，本轮只问：" + FIELDS[missing[0]])
        instruction = "本轮只追问这一项：" + FIELDS[missing[0]] + "。用一句自然的问题，不要输出摘要。"
    else:
        log("流程", "两项信息均已满足，进入摘要阶段")
        instruction = (
            "信息收集完成。输出简短的售后咨询摘要，包含商品和具体问题，"
            "并说明摘要仅供后续咨询使用，尚未提交售后申请。不要再追问。"
        )
    # 3. 每轮使用当前任务创建 Agent；完整对话历史会在调用时传入。
    # 不开放业务工具，因此本例只能追问和整理摘要，不能办理售后。
    log("Agent", f"创建对话助手，传入历史消息 {len(messages)} 条，无业务工具")
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
    log("Agent", "开始生成回复")
    started = perf_counter()
    try:
        response = agent.invoke({"messages": messages}, config={"recursion_limit": 6})
    finally:
        log("Agent", f"本次调用耗时：{perf_counter() - started:.2f} 秒")
    reply = response["messages"][-1].content
    log("Agent回复", reply, core=True)
    # 4. 助手回复仅加入对话历史，不加入供 Jev 检查的用户陈述。
    messages.append({"role": "assistant", "content": reply})
    log("流程", "本轮结束：摘要已输出" if not missing else "本轮结束：等待用户补充")
    return not missing


def main():
    """初始化客户端，并运行预设演示或键盘交互会话。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interactive", action="store_true", help="改为键盘输入，输入 exit 退出")
    parser.add_argument("--threshold", type=float, default=0.8)
    args = parser.parse_args()
    if not 0 <= args.threshold <= 1:
        parser.error("阈值必须在 0～1 之间")
    log("系统", f"启动售后咨询，模式：{'键盘交互' if args.interactive else '预设演示'}，门槛：{args.threshold:.2f}")
    # 两份历史均只保存在内存中，重新运行脚本会开始新会话。
    messages, user_statements = [], []
    log("系统", "正在初始化 Agent 模型和 Jev 客户端")
    model = create_agent_model()
    with create_client() as client:
        log("系统", "客户端初始化完成；尚未发送模型请求")
        turns = iter(DEMO_TURNS)
        while True:
            text = input("[核心][用户输入] 你：").strip() if args.interactive else next(turns, None)
            if text is None:
                log("系统", "预设消息已结束；若仍有缺项，可用 --interactive 继续体验新会话。", core=True)
                break
            if text.lower() == "exit":
                log("系统", "用户主动退出咨询", core=True)
                break
            if not text.strip():
                log("流程", "输入为空，请重新输入；本次不调用模型", core=True)
                continue
            log("流程", f"第 {len(user_statements) + 1} 轮开始")
            if not args.interactive:
                log("用户输入", "预设消息：" + text, core=True)
            # 先保存本轮原话，再检查累计信息，支持跨轮补充。
            user_statements.append(text)
            messages.append({"role": "user", "content": text})
            if run_turn(client, model, user_statements, messages, args.threshold):
                log("系统", "咨询信息收集完成，会话结束；未提交售后申请", core=True)
                break
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EOFError, KeyboardInterrupt):
        log("系统", "已结束咨询。", core=True)
    except Exception as error:
        log("错误", f"本轮未完成：{type(error).__name__}，请检查配置或网络后重试。", error=True)
        raise SystemExit(1)
