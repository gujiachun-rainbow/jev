"""TypeSafe 入门：一次请求分析客服工单的三个维度。"""

import argparse
import json
import sys
from time import perf_counter

from typesafe_sdk import (
    Choice, Noul, Score,
    TypeSafeAPIError, TypeSafeError,
)

from runtime import create_client

DEFAULT_TICKET = (
    "我已经尝试连接 Stripe 账户三天了，但支付集成一直报错。"
    "这导致客户无法付款，我正在损失订单，请尽快帮我解决！"
)
DEPARTMENTS = {"billing": "账单团队", "technical": "技术支持", "sales": "销售团队"}


def main() -> int:
    parser = argparse.ArgumentParser(description="使用 TypeSafe 分析客服工单")
    parser.add_argument("ticket", nargs="?", default=DEFAULT_TICKET, help="要分析的工单文本")
    parser.add_argument("--json", action="store_true", help="输出完整的 API JSON 响应")
    args = parser.parse_args()
    if not args.ticket.strip():
        parser.error("工单内容不能为空")

    try:
        with create_client() as client:
            start = perf_counter()
            try:
                result = client.system_one(
                    # state 是待分析的内容；questions 是希望模型回答的问题。
                    state=args.ticket,
                    questions={
                        "department": Choice(
                            instructions="哪个团队最适合处理这条工单？按问题根因分类。",
                            criteria={
                                "billing": "扣费、退款、账单或订阅问题",
                                "technical": "软件故障、报错或系统集成问题",
                                "sales": "购买咨询、报价或套餐选择",
                            },
                        ),
                        "frustration": Score(
                            instructions="客户表达出的不满程度如何？",
                            # 顺序决定分值：0、1、2。
                            criteria=["平静地陈述事实", "不满但仍保持礼貌", "非常愤怒，措辞激烈"],
                        ),
                        "is_urgent": Noul(
                            instructions="这条工单是否表达了紧迫性或需要尽快处理？",
                        ),
                    },
                )
            finally:
                # 写入 stderr，让 --json 的 stdout 保持纯 JSON。
                print(f"API 调用耗时：{(perf_counter() - start) * 1000:.2f} ms", file=sys.stderr)
    except TypeSafeAPIError as error:
        print(f"API 请求失败（HTTP {error.status}），请检查 Key、账户额度或服务状态。", file=sys.stderr)
        return 1
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except TypeSafeError:
        print("调用失败，请检查 Key 格式、网络连接，或稍后重试。", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.raw_http_response.json(), ensure_ascii=False, indent=2))
    else:
        department = result.choices["department"]
        print(f"工单：{args.ticket}")
        print(f"处理部门：{DEPARTMENTS.get(department.choice, department.choice)}")
        print(f"分类置信度：{department.confidence:.2f}")
        print(f"不满评分：{result.scores['frustration'].score:.2f}（0 平静 / 1 不满 / 2 愤怒）")
        print(f"判定为紧急的概率：{result.nouls['is_urgent'].noul:.2f}（不是紧急程度评分）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
