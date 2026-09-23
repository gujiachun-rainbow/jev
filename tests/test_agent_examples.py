"""验证关键业务分支；使用替身，不发起外部 API 请求。"""

import contextlib
import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from agent_case_router import select_route, lookup_order
from agent_case_jev_tool import evaluate_products, within_budget
from agent_case_followup import missing_information


class AgentExampleTests(unittest.TestCase):
    def test_configurable_route_threshold_boundary(self):
        answer = SimpleNamespace(choice='logistics', confidence=0.65)
        self.assertEqual(select_route(answer, 0.65), 'logistics')
        self.assertEqual(select_route(answer, 0.66), 'clarify')

    def test_configurable_presence_threshold_boundary(self):
        result = SimpleNamespace(nouls={
            key: SimpleNamespace(noul=0.8) for key in ('environment', 'symptom', 'steps')
        })
        self.assertEqual(missing_information(result, 0.8), [])
        self.assertEqual(len(missing_information(result, 0.81)), 3)

    def test_invalid_thresholds_are_rejected(self):
        for threshold in (-0.1, 1.1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                select_route(None, threshold)
            with self.assertRaises(ValueError):
                missing_information(None, threshold)

    def test_router_uncertainty_and_unknown_intent(self):
        for choice, confidence in [('logistics', 0.49), ('unclear', 1.0), ('unexpected', 1.0)]:
            self.assertEqual(select_route(SimpleNamespace(choice=choice, confidence=confidence)), 'clarify')
        self.assertEqual(select_route(SimpleNamespace(choice='aftersales', confidence=0.9)), 'aftersales')

    def test_unknown_order_does_not_fabricate_status(self):
        with contextlib.redirect_stdout(io.StringIO()):
            result = lookup_order.invoke({'order_id': 'DOES-NOT-EXIST'})
        self.assertIn('error', result)
        self.assertNotIn('status', result)

    def test_budget_boundary_is_checked_in_python(self):
        self.assertEqual([p['id'] for p in within_budget(4999)], ['P1'])
        self.assertEqual(within_budget(4998), [])
        self.assertNotIn('P3', [p['id'] for p in within_budget(6000)])

    def test_empty_candidates_skip_jev(self):
        with patch('agent_case_jev_tool.create_client') as create_client, contextlib.redirect_stdout(io.StringIO()):
            result = evaluate_products.invoke({'requirements': '办公', 'max_price': 100})
        self.assertEqual(result['products'], [])
        create_client.assert_not_called()

    def test_invalid_budget_skips_jev(self):
        with patch('agent_case_jev_tool.create_client') as create_client, contextlib.redirect_stdout(io.StringIO()):
            result = evaluate_products.invoke({'requirements': '办公', 'max_price': 0})
        self.assertIn('error', result)
        create_client.assert_not_called()

    def test_uncertain_information_requires_followup(self):
        result = SimpleNamespace(nouls={
            'environment': SimpleNamespace(noul=0.99),
            'symptom': SimpleNamespace(noul=0.6),
            'steps': SimpleNamespace(noul=0.1),
        })
        self.assertEqual(missing_information(result), ['具体症状或报错', '触发问题的操作步骤'])
        for answer in result.nouls.values():
            answer.noul = 0.99
        self.assertEqual(missing_information(result), [])


if __name__ == '__main__':
    unittest.main()
