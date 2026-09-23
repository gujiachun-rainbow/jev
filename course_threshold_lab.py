"""课堂离线实验：固定假想回答，只改变业务阈值；不调用 API，不需要 Key。

运行：.venv/bin/python course_threshold_lab.py
这些数值是人工构造的教学输入，不是 Jev 实测输出或质量评测结果。
"""

from types import SimpleNamespace

from agent_case_followup import missing_information
from agent_case_router import select_route


def main():
    print('离线实验：人工构造回答，不代表 Jev 的实测表现。')
    answer = SimpleNamespace(choice='logistics', confidence=0.65)
    print('\n同一个 Choice 回答：choice=logistics, confidence=0.65')
    for threshold in (0.5, 0.65, 0.8):
        print(f'阈值 {threshold:.2f} → {select_route(answer, threshold)}')

    answer = SimpleNamespace(choice='unclear', confidence=0.99)
    print('\n高置信度也可能是在确信“无法归类”：')
    print(f'choice=unclear, confidence=0.99 → {select_route(answer)}')

    result = SimpleNamespace(nouls={
        'environment': SimpleNamespace(noul=0.95),
        'symptom': SimpleNamespace(noul=0.70),
        'steps': SimpleNamespace(noul=0.80),
    })
    print('\n同一组 Noul 回答：环境=0.95，症状=0.70，步骤=0.80')
    for threshold in (0.6, 0.8, 0.9):
        missing = missing_information(result, threshold)
        print(f'阈值 {threshold:.2f} → 待补充：{missing or "无；允许提供手册工具"}')
    print('\n讨论：减少追问会增加什么风险？这些固定回答能否证明模型准确？')


if __name__ == '__main__':
    main()
