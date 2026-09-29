"""Jev Hello World：判断一句话是否在打招呼。"""

from typesafe_sdk import Noul

from runtime import create_client


def main():
    text = "Hello, world! 你好，Jev！"
    with create_client() as client:
        result = client.system_one(
            state=text,
            questions={
                "is_greeting": Noul(instructions="这句话是否在打招呼或表达问候？"),
            },
        )

    probability = result.nouls["is_greeting"].noul
    print(f"输入：{text}")
    print(f"打招呼的概率：{probability:.2f}")


if __name__ == "__main__":
    main()
