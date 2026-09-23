"""案例三：Jev 检查信息完整度 → Agent 追问 → 信息齐全后允许查询排查手册。

运行：.venv/bin/python agent_case_followup.py
默认演示两轮预设用户消息；也可 --scenario incomplete 或 --scenario complete。
"""

import argparse
import json
import sys
from time import perf_counter

from langchain.agents import create_agent
from langchain.tools import tool
from typesafe_sdk import Noul, NoulCriteria

from agent_config import create_agent_model
from runtime import create_client

LABELS = {'environment': '运行环境或浏览器', 'symptom': '具体症状或报错', 'steps': '触发问题的操作步骤'}


@tool
def lookup_troubleshooting() -> dict:
    """读取演示报表导出排查手册，只提供排查建议，不执行任何系统操作。"""
    print('[工具] lookup_troubleshooting()')
    return {
        'source': '演示知识库 / 导出问题排查 v1',
        'steps': ['确认浏览器版本和导出格式', '用其他浏览器复现以区分浏览器兼容问题',
                  '记录报错时间和请求 ID，交给管理员查询服务端日志'],
        'note': 'HTTP 500 只能说明服务端报错，不能据此确定唯一根因。',
    }


def missing_information(result, presence_threshold=0.8):
    # Noul 是“该信息存在”的概率。低于阈值先追问，不视为已经准备好。
    if not 0 <= presence_threshold <= 1:
        raise ValueError('信息存在概率阈值必须在 0～1 之间')
    return [label for key, label in LABELS.items() if result.nouls[key].noul < presence_threshold]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=['both', 'incomplete', 'complete'], default='both')
    parser.add_argument('--presence-threshold', type=float, default=0.8, help='信息存在概率阈值，默认 0.8')
    args = parser.parse_args()
    if not 0 <= args.presence_threshold <= 1:
        parser.error('信息存在概率阈值必须在 0～1 之间')
    initial = '报表导出有问题，帮我看一下。'
    supplement = '我用 macOS 上的 Safari 18。进入销售报表，选择九月，再点导出 PDF，就提示 HTTP 500。'
    turns = {'both': [initial, supplement], 'incomplete': [initial],
             'complete': [initial + supplement]}[args.scenario]
    messages, user_statements = [], []
    model = create_agent_model()
    with create_client() as client:
        for number, text in enumerate(turns, 1):
            print(f'\n第 {number} 轮，预设用户输入：{text}')
            user_statements.append(text)
            messages.append({'role': 'user', 'content': text})
            start = perf_counter()
            try:
                result = client.system_one(
                    # 只检查用户实际提供的信息，不能把 Agent 追问里的示例当作事实。
                    state={'user_statements': user_statements},
                    questions={
                        'environment': Noul(instructions='用户是否提供了具体运行环境或浏览器？',
                            criteria=NoulCriteria(true='明确提到操作系统、浏览器或客户端', false='未提及具体环境')),
                        'symptom': Noul(instructions='用户是否描述了可识别的具体症状或报错？',
                            criteria=NoulCriteria(true='具体描述错误提示或异常表现', false='只说有问题、不好用等笼统说法')),
                        'steps': Noul(instructions='用户是否说明了触发问题的具体操作过程？',
                            criteria=NoulCriteria(true='说明了在哪个页面进行哪些操作', false='没有操作过程或只有泛泛的功能名称')),
                    },
                )
            finally:
                print(f'Jev 信息检查耗时：{(perf_counter() - start) * 1000:.2f} ms')
            missing = missing_information(result, args.presence_threshold)
            print(f'信息存在概率阈值：{args.presence_threshold:.2f}')
            print('检查概率：', json.dumps({key: answer.noul for key, answer in result.nouls.items()}, ensure_ascii=False))

            # 工具权限由代码决定：信息不足时，Agent 根本拿不到排查工具。
            if missing:
                tools = []
                instruction = '只针对以下缺失信息提出简短问题，不猜测原因：' + '、'.join(missing)
            else:
                tools = [lookup_troubleshooting]
                instruction = '信息已经齐全。必须调用 lookup_troubleshooting，再依据手册和用户事实提出排查建议。'
            print('当前流程：', '追问缺失信息' if missing else '查询手册并给出建议')
            agent = create_agent(model=model, tools=tools, system_prompt=(
                '你是中文技术支持 Agent。' + instruction +
                '不要编造系统状态、根因或处理结果。手册是演示数据，回复简洁。'
            ))
            start = perf_counter()
            try:
                response = agent.invoke({'messages': messages}, config={'recursion_limit': 12})
            finally:
                print(f'Agent 本轮耗时（含工具）：{(perf_counter() - start) * 1000:.2f} ms')
            final = response['messages'][-1].content
            print('Agent 回复：', final)
            # 用普通消息列表维护当前进程中的对话，重新运行脚本时会重置。
            messages.append({'role': 'assistant', 'content': final})


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'运行失败：{type(error).__name__}，请检查 API 配置、额度或网络。', file=sys.stderr)
        raise SystemExit(1)
