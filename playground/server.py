"""从项目根目录运行 python -m playground.server。"""

import argparse
import os
import logging
from pathlib import Path
from time import perf_counter
from typing import Annotated, Literal

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, StringConstraints, model_validator

from dotenv import load_dotenv
from typesafe_sdk import Choice, Noul, NoulCriteria, Score

from runtime import create_client

ROOT = Path(__file__).resolve().parents[1]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class EvaluationRequest(BaseModel):
    mode: Literal["noul", "choice", "score"]
    state: Text
    instructions: Text
    criteria: Annotated[dict[str, Text] | list[Text], Field(min_length=2, max_length=20)]

    @model_validator(mode="after")
    def check_criteria(self):
        if self.mode == "score":
            if not isinstance(self.criteria, list):
                raise ValueError("评分标准必须为有序数组")
        elif not isinstance(self.criteria, dict):
            raise ValueError("判断和选择标准必须为对象")
        elif self.mode == "noul" and set(self.criteria) != {"true", "false"}:
            raise ValueError("判断标准必须包含 true 和 false")
        elif any(not key.strip() for key in self.criteria):
            raise ValueError("选项名称不能为空")
        return self

    def question(self):
        constructor = {"noul": Noul, "choice": Choice, "score": Score}[self.mode]
        criteria = NoulCriteria(**self.criteria) if self.mode == "noul" else self.criteria
        return constructor(instructions=self.instructions, criteria=criteria)


def evaluate(data: EvaluationRequest):
    start = perf_counter()
    with create_client() as client:
        result = client.system_one(state=data.state, questions={"evaluation": data.question()})
    mode = data.mode
    collection = {"noul": result.nouls, "choice": result.choices, "score": result.scores}[mode]
    evaluation = collection["evaluation"]
    answer = {mode: getattr(evaluation, mode)}
    if mode != "noul":
        answer["probabilities"] = evaluation.probabilities
        answer["confidence"] = evaluation.confidence
    return {
        "mode": mode, "model": "jev-latest",
        "elapsed_ms": round((perf_counter() - start) * 1000, 2),
        "input": data.model_dump(exclude={"mode"}),
        "answer": answer,
    }


app = FastAPI(title="Jev 判断实验室", version="1.0.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
def health():
    load_dotenv(ROOT / ".env")
    return {"configured": bool(os.getenv("TYPESAFE_API_KEY", "").strip()),
            "model": "jev-latest"}


@app.exception_handler(RequestValidationError)
async def invalid_input(request: Request, error: RequestValidationError):
    return JSONResponse({"error": "输入格式无效，请检查模式、文本和判定标准。"}, status_code=400)


@app.post("/api/evaluate")
def evaluate_request(data: EvaluationRequest):
    # 同步路由由 FastAPI 在线程池执行，SDK 调用不会阻塞其他请求。
    if not health()["configured"]:
        return JSONResponse({"error": "请在项目根目录 .env 中配置 TYPESAFE_API_KEY，然后重新运行。"}, status_code=503)
    try:
        return evaluate(data)
    except Exception as error:
        logging.getLogger(__name__).error("Jev request failed: %s", type(error).__name__)
        return JSONResponse({"error": "Jev 调用失败，请检查 API Key、额度或网络后重试。"}, status_code=502)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
