"""第五章：预算过滤 → Jev 匹配评分 → Python 输出推荐建议。"""

import argparse
import json
import math

from typesafe_sdk import Score, TypeSafeError

from runtime import create_client


# 虚构教学商品，价格单位为元；不代表真实商品报价或性能。
PRODUCTS = [
    {"id": "P1", "name": "轻行本", "price": 4999, "weight_kg": 1.2,
     "description": "适合办公、视频会议和通勤；集成显卡，不适合大型游戏"},
    {"id": "P2", "name": "游戏本", "price": 5999, "weight_kg": 2.5,
     "description": "独立显卡，适合游戏与三维设计，机身较重"},
    {"id": "P3", "name": "旗舰轻薄本", "price": 8999, "weight_kg": 1.1,
     "description": "适合移动办公，轻便且性能充足"},
]
CRITERIA = [
    "与用户核心用途或明确偏好冲突",
    "满足部分需求，但存在明显取舍",
    "符合核心用途和明确偏好",
]
MIN_SCORE = 1.5       # 三个等级对应 0～2；这是教学门槛。
MIN_CONFIDENCE = 0.5  # 与匹配分数不同，单独控制判断可靠性。


def build_questions(candidates):
    return {
        item["id"]: Score(
            instructions={
                "question": "candidate 与用户的用途和偏好有多匹配？预算已由代码过滤。",
                "rules": "只依据商品资料和用户需求，不补造参数；资料不足时不要假定满足。",
                "candidate": item,
            },
            criteria=CRITERIA,
        ) for item in candidates
    }


def select_products(candidates, scores):
    evaluated = []
    for item in candidates:
        answer = scores.get(item["id"])
        if answer is None or not 0 <= answer.score <= 2 or not 0 <= answer.confidence <= 1:
            raise ValueError("评分缺失或超出有效范围")
        if answer.confidence < MIN_CONFIDENCE:
            decision = "needs_review"
        elif answer.score < MIN_SCORE:
            decision = "low_match"
        else:
            decision = "eligible"
        evaluated.append({**item, "match_score": answer.score,
                          "confidence": answer.confidence, "decision": decision})
    # 同分时优先较低价格，再按 ID，保证固定输入的输出顺序稳定。
    evaluated.sort(key=lambda item: (-item["match_score"], item["price"], item["id"]))
    recommendations = [item for item in evaluated if item["decision"] == "eligible"][:1]
    if recommendations:
        status, note = "recommended", "从同时达到匹配与置信度门槛的商品中推荐一款。"
    elif any(item["decision"] == "needs_review" for item in evaluated):
        status, note = "needs_review", "部分判断不确定，暂不推荐；请补充需求或核实商品资料。"
    else:
        status, note = "no_match", "预算内商品均未达到匹配门槛，请调整偏好或扩充候选。"
    return {"status": status, "note": note, "recommendations": recommendations,
            "evaluated": evaluated}


def recommend(requirements, max_price):
    missing = []
    if not requirements.strip():
        missing.append("requirements")
    if max_price is None:
        missing.append("max_price")
    if missing:
        return {"status": "needs_input", "missing_fields": missing,
                "note": "请补充用途偏好和最高预算。", "recommendations": []}
    if not math.isfinite(max_price) or max_price <= 0:
        return {"status": "invalid_input", "note": "预算必须是大于零的有限数值。",
                "recommendations": []}
    candidates = [item for item in PRODUCTS if item["price"] <= max_price]
    if not candidates:
        return {"status": "no_candidates", "note": "演示商品库中没有预算内商品。",
                "recommendations": []}
    try:
        with create_client() as client:
            result = client.system_one(
                state={"requirements": requirements},
                questions=build_questions(candidates),
            )
        return select_products(candidates, result.scores)
    except (TypeSafeError, ValueError) as error:
        return {"status": "evaluation_failed", "error_type": type(error).__name__,
                "note": "未获得有效评分，请检查配置或稍后重试。", "recommendations": []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirements", nargs="?", default="")
    parser.add_argument("--budget", type=float, default=None, help="最高预算，单位为元")
    args = parser.parse_args()
    output = recommend(args.requirements, args.budget)
    output.update({"source": "虚构教学商品库", "score_range": [0, 2],
                   "min_score": MIN_SCORE, "min_confidence": MIN_CONFIDENCE})
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 1 if output["status"] in {"invalid_input", "evaluation_failed"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
