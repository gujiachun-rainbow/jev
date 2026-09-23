# TypeSafe Python 入门案例

一个客服工单分析命令行程序，使用官方 Python SDK 调用 `jev-latest`。

## Jev 开发者课程

面向已经会使用 LangChain Agent 的开发者，按“结构化判断 → 问题设计 → 三种 Agent 接入模式 → 验证与综合练习”学习。

- [HTML 学员讲义](docs/course.html)：浏览器直接打开，包含 8 章正文、案例代码、练习答案、离线阈值实验与打印版式；支持手机阅读。
- [课程大纲](docs/COURSE_OUTLINE.md)：8 章，共 6 小时课堂与 2 小时课后作业，包含教学目标、案例映射及验收标准。
- [课堂实验手册](docs/COURSE_LABS.md)：逐章运行步骤、对照输入、练习和评测记录方式。
- [离线阈值实验](course_threshold_lab.py)：固定人工构造的模型回答，复用案例分支函数观察阈值影响，不联网、不需要 Key（需安装项目依赖）。

```bash
.venv/bin/python course_threshold_lab.py
# 以下两条会调用远程 API
.venv/bin/python agent_case_router.py --min-confidence 0.8
.venv/bin/python agent_case_followup.py --presence-threshold 0.9
```

两项阈值默认仍为 0.5 和 0.8，仅作教学示例。路由打印类别概率与置信度，便于区分两者；多轮检查打印本轮使用的概率阈值。

## 安装和运行

需要 Python 3.10 或更新版本。在项目目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

首次配置时，将 `.env.example` 复制为 `.env`，填入自己的 API Key：

```dotenv
TYPESAFE_API_KEY=your_api_key_here
```

如果已有 `.env`，直接使用即可；系统环境变量中的同名配置优先。`.env` 已加入 `.gitignore`。

```bash
# 分析默认的中文工单
python main.py

# 换成自己的文本
python main.py "我昨天被重复扣款了，请帮我退款。"

# 查看完整响应（包含模型、答案与用量等服务端返回字段）
python main.py --json
```

## 代码怎么理解

`state` 是工单文本，`questions` 是问题字典。一次请求同时分析：

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| department | Choice | 从 billing、technical、sales 中选择负责团队 |
| frustration | Score | 根据有序标准评分：0 平静、1 不满、2 愤怒 |
| is_urgent | Noul | 返回 0～1 的判断值，越大越支持“紧急” |

结果分别通过 `result.choices`、`result.scores`、`result.nouls` 读取。
Score 的标准按列表顺序从 0 编号，返回值可能是小数；Noul 也不是 Python 布尔值。
模型输出可能变化，示例只展示分析结果，不会自动派单。

每次运行会向 TypeSafe 发送工单文本并调用一次 API，可能消耗账户额度。
示例设置 60 秒请求超时，并关闭自动重试，便于观察第一次请求的结果。

参考：[官方快速入门](https://docs.typesafe.ai/introduction/quickstart)、[Python SDK 用法](https://docs.typesafe.ai/sdk/python/usage)。

## 更多中文案例

每个案例单独放在一个 Python 文件中，包含输入、问题定义、API 调用和结果解释，均有中文注释。建议按下面的顺序学习。

| 学习顺序 | 独立文件 | 内容 |
| --- | --- | --- |
| 1 | [case_choice.py](case_choice.py) | 电商售后分类 |
| 2 | [case_score.py](case_score.py) | 软件缺陷评分 |
| 3 | [case_noul.py](case_noul.py) | 客服条件判断 |
| 4 | [case_advanced.py](case_advanced.py) | 结构化指令与标准 |
| 5 | [case_matching.py](case_matching.py) | 动态生成商品匹配问题 |
| 6 | [case_mixed.py](case_mixed.py) | 三种类型联合分诊 |

每个文件按 `build_case()` → `main()` → `interpret()` 阅读：先理解输入与问题，再看调用过程，最后看答案如何用于业务判断。修改 `build_case()` 中的 `state` 或 `questions` 即可尝试自己的场景。

在项目目录直接运行任意一个文件：

```bash
.venv/bin/python case_choice.py
.venv/bin/python case_score.py
.venv/bin/python case_noul.py
.venv/bin/python case_advanced.py
.venv/bin/python case_matching.py
.venv/bin/python case_mixed.py
```

每次运行调用一次 API，直接在案例代码中计时并打印：

```python
start = perf_counter()
try:
    result = client.system_one(state=data["state"], questions=data["questions"])
finally:
    print(f"API 调用耗时：{(perf_counter() - start) * 1000:.2f} ms", file=sys.stderr)
```

耗时包含网络和服务端处理，是一次完整 API 调用的耗时。请求成功或失败都会打印。耗时输出到 stderr，方便与结果分开，也保证 `main.py --json` 输出有效 JSON。

`runtime.py` 仅共用客户端和 Key 配置。无需单独的日志或性能统计脚本。

Noul 表示回答为“是”的概率，程度评分应使用 Score。案例里的业务阈值仅用于演示。

参考文档：[Choice](https://docs.typesafe.ai/primitives/choice)、[Score](https://docs.typesafe.ai/primitives/score)、[Noul](https://docs.typesafe.ai/primitives/noul)、[Advanced structure](https://docs.typesafe.ai/primitives/advanced)。

## Jev + LangChain + DeepSeek Agent 案例

三个独立文件，建议按顺序学习。Jev 负责结构化判断，DeepSeek 负责工具选择、对话和回复，LangChain `create_agent` 负责模型与工具的执行循环。

| 文件 | 典型模式 | Jev 的位置 | Agent 的职责 |
| --- | --- | --- | --- |
| [agent_case_router.py](agent_case_router.py) | 客服请求分流 | Agent 之前的固定节点，使用 Choice | 调用订单或售后规则工具并回复 |
| [agent_case_jev_tool.py](agent_case_jev_tool.py) | 商品筛选推荐 | Agent 调用的工具内部，使用 Score | 提取需求、调用筛选工具、解释推荐理由 |
| [agent_case_followup.py](agent_case_followup.py) | 多轮补全与排查 | 每轮对话前检查信息，使用 Noul | 缺信息时追问，齐全后查询手册并建议 |

### 配置和运行

依赖要求 Python 3.10+。安装命令：

```bash
uv pip install --python .venv/bin/python -r requirements.txt
# 如果使用 pip：先激活虚拟环境，再运行 python -m pip install -r requirements.txt
```

现有 `.env` 已配置两家的 Key；新环境参考 `.env.example`。Key 不放进案例源码。

```dotenv
TYPESAFE_API_KEY=your_typesafe_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_MODEL=deepseek-v4-flash
```

按用户指定的 `deepseek-v4-flash` 发起请求。根据 2026-09-22 查阅的 DeepSeek 官方说明，这个名称仍被接受，但服务端现已将其映射到 DeepSeek-V4.1-Flash；保留名称不代表固定旧模型权重。可通过 `DEEPSEEK_MODEL` 调整请求名称。案例使用非思考模式，60 秒单次模型请求超时，关闭自动重试，Agent 图的递归上限为 12。

```bash
# 1. Jev 分流，DeepSeek Agent 调用物流工具
.venv/bin/python agent_case_router.py

# 改走售后 Agent
.venv/bin/python agent_case_router.py "我想退货，请告诉我需要什么材料。"

# 2. Agent 主动调用包含 Jev 的评分工具
.venv/bin/python agent_case_jev_tool.py

# 换一种产品需求
.venv/bin/python agent_case_jev_tool.py "预算6000元，主要玩游戏，不在乎重量。"

# 3. 自动演示两轮预设用户消息：先追问，再排查
.venv/bin/python agent_case_followup.py

# 单独观察信息不足或信息齐全的分支
.venv/bin/python agent_case_followup.py --scenario incomplete
.venv/bin/python agent_case_followup.py --scenario complete
```

### 每个案例怎么看

**案例一：分类与执行分开。** `select_route()` 读取 Jev 的类别与置信度，由 Python 选择专业 Agent 和工具集合。低置信度或未知诉求会澄清，不启动专业 Agent。订单不存在时工具返回错误，Agent 应提示核对。

**案例二：Jev 变成 Agent 的工具。** `@tool` 将 `evaluate_products()` 暴露给 DeepSeek。Agent 从用户请求中提取需求与预算，Python 先做价格过滤，再在一次 Jev 调用中为各候选商品评分，Agent 阅读工具返回值生成推荐。没有预算先追问，没有候选不调用 Jev。工具调用参数会打印出来，方便学习。

**案例三：多轮对话由程序控制。** 每轮仅将用户真实提供的信息交给 Jev，避免把 Agent 追问中的示例误当成事实。信息不足时工具列表为空；齐全后才提供 `lookup_troubleshooting`。默认两轮输入是脚本里的预设演示，不是自动模拟真实用户，也不会等键盘输入。对话只保存在当前进程的消息列表中。

工具选择是模型行为，提示词要求不等于生产权限控制。真实系统应在工具函数中验证参数、身份和资源归属；本项目工具都是只读演示，没有执行退款、修改订单或修改系统的能力。

### 耗时打印

每个案例直接在调用前后用 `perf_counter()` / `print()` 打印，无单独日志框架或批量性能统计脚本：

- **Jev 耗时**：一次完整 SDK 请求的端到端耗时。
- **Agent 耗时**：一次 `agent.invoke()`，可能包含多次 DeepSeek 请求以及工具执行。
- 案例二的 Agent 总耗时已经包含工具内的 Jev 时间，不能重复相加。
- API 请求异常时也通过 `finally` 打印耗时，终端仅显示错误类型，避免输出含敏感信息的完整异常。

业务数据、商品和手册均为本地虚构数据；Jev 与 DeepSeek 则是真实的远程 API 调用，会产生相应请求用量。Agent 工具调用次数可能变化。`agent_config.py` 只共享模型配置，原有 Jev 入门案例不变。

参考：[LangChain create_agent](https://reference.langchain.com/python/langchain/agents/factory/create_agent)、[ChatDeepSeek 集成](https://docs.langchain.com/oss/python/integrations/chat/deepseek)、[DeepSeek API 与模型名称](https://api-docs.deepseek.com/)、[Jev 意图路由](https://docs.typesafe.ai/patterns/intent-routing)。

### 验证情况

此前已使用真实 API 验证物流分流、售后分流、Agent 调用 Jev 商品评分工具，以及信息不足→补充信息→调用手册的两轮流程，均成功；该记录不代表课程适配后重新进行远程验证。另有九项不联网测试覆盖低置信度分流、未知订单、预算边界、空候选、非法预算、信息不足判断以及新增的阈值边界和非法阈值：

```bash
.venv/bin/python -m unittest discover -s tests -v
```
