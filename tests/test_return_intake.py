"""验证售后咨询的多轮策略，不访问远程模型。"""

import contextlib
import io
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import agent_case_return_intake as intake


def answer(product, problem):
    return SimpleNamespace(nouls={
        "product": SimpleNamespace(noul=product),
        "problem": SimpleNamespace(noul=problem),
    })


class ReturnIntakeTests(unittest.TestCase):
    def test_missing_information_and_boundaries(self):
        cases = [
            (0.1, 0.1, ["product", "problem"]),
            (0.9, 0.2, ["problem"]),
            (0.2, 0.9, ["product"]),
            (0.8, 0.8, []),
            (0.79, 0.8, ["product"]),
            (float("nan"), 0.9, ["product"]),
        ]
        for product, problem, expected in cases:
            with self.subTest(product=product, problem=problem):
                self.assertEqual(intake.missing_information(answer(product, problem)), expected)
        self.assertEqual(intake.missing_information(SimpleNamespace(nouls={})), ["product", "problem"])
        for threshold in [-1, 1.1, float("nan")]:
            with self.assertRaises(ValueError):
                intake.missing_information(answer(0.9, 0.9), threshold)

    def test_three_turns_keep_assistant_examples_out_of_evidence(self):
        client = Mock()
        client.system_one.side_effect = [answer(0.1, 0.1), answer(0.9, 0.1), answer(0.9, 0.9)]
        messages, statements = [], []
        with patch.object(intake, "create_agent") as factory, contextlib.redirect_stdout(io.StringIO()):
            factory.return_value.invoke.return_value = {
                "messages": [SimpleNamespace(content="示例：杯子有裂缝吗？")],
            }
            for index, text in enumerate(intake.DEMO_TURNS):
                statements.append(text)
                messages.append({"role": "user", "content": text})
                self.assertEqual(intake.run_turn(client, object(), statements, messages), index == 2)
                evidence = client.system_one.call_args.kwargs["state"]["user_statements"]
                self.assertEqual(evidence, intake.DEMO_TURNS[:index + 1])
                self.assertNotIn("杯子", "".join(evidence))
            prompts = [call.kwargs["system_prompt"] for call in factory.call_args_list]
            self.assertIn("本轮只追问这一项：商品名称或类型", prompts[0])
            self.assertIn("本轮只追问这一项：具体问题或异常表现", prompts[1])
            self.assertIn("信息收集完成", prompts[2])
            self.assertTrue(all(call.kwargs["tools"] == [] for call in factory.call_args_list))

    def test_jev_failure_does_not_invoke_agent(self):
        client = Mock()
        client.system_one.side_effect = RuntimeError("request failed")
        with patch.object(intake, "create_agent") as factory:
            with self.assertRaises(RuntimeError):
                intake.run_turn(client, object(), ["售后咨询"], [])
            factory.assert_not_called()

    def test_complete_first_message_ends_interactive_session(self):
        with patch.object(intake, "create_client"), patch.object(intake, "create_agent_model"), \
                patch.object(intake, "run_turn", return_value=True) as turn, \
                patch("builtins.input", return_value="蓝牙耳机左耳无声") as user_input, \
                patch("sys.argv", ["intake", "--interactive"]):
            self.assertEqual(intake.main(), 0)
            turn.assert_called_once()
            user_input.assert_called_once()


if __name__ == "__main__":
    unittest.main()
