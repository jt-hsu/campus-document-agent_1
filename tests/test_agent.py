import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent import run_agent
from llm_client import LLMConnectionError, LLMResponseError


class AgentWorkflowTests(unittest.TestCase):
    def test_valid_evidence(self):
        def fake_llm(q, evidence):
            return {"supported": True, "answer": "不會；扣減仍依規定辦理。", "evidence_ids": ["E1"]}
        out = run_agent("銷過之後操行分數會恢復嗎？", llm_fn=fake_llm)
        self.assertEqual(out["status"], "answered")
        self.assertEqual(out["sources"][0]["article"], "第四條")
        self.assertTrue(any(s["step"] == "Tool Call" for s in out["trace"]))

    def test_no_result_bypasses_llm(self):
        def fail_if_called(*args):
            raise AssertionError("no_result 時不應呼叫 LLM")
        out = run_agent("請問咖啡廳珍珠奶茶多少錢？", llm_fn=fail_if_called)
        self.assertEqual(out["status"], "no_result")

    def test_empty_bypasses_search(self):
        def fail_if_called(*args, **kwargs):
            raise AssertionError("空白輸入不應呼叫檢索")
        out = run_agent("  ", search_fn=fail_if_called)
        self.assertEqual(out["status"], "invalid_input")

    def test_llm_unavailable(self):
        def fake_llm(q, evidence):
            raise LLMConnectionError("connection refused")
        out = run_agent("銷過之後操行分數會恢復嗎？", llm_fn=fake_llm)
        self.assertEqual(out["status"], "llm_connection_error")

    def test_llm_bad_format(self):
        def fake_llm(q, evidence):
            raise LLMResponseError("not JSON")
        out = run_agent("銷過之後操行分數會恢復嗎？", llm_fn=fake_llm)
        self.assertEqual(out["status"], "llm_response_error")

    def test_insufficient_evidence(self):
        def fake_llm(q, evidence):
            return {"supported": False, "answer": "無法回答", "evidence_ids": []}
        out = run_agent("銷過之後操行分數會恢復嗎？", llm_fn=fake_llm)
        self.assertEqual(out["status"], "insufficient_evidence")

    def test_fabricated_source_blocked(self):
        def fake_llm(q, evidence):
            return {"supported": True, "answer": "亂回答", "evidence_ids": ["E99"]}
        out = run_agent("銷過之後操行分數會恢復嗎？", llm_fn=fake_llm)
        self.assertEqual(out["status"], "invalid_evidence_ids")


if __name__ == "__main__":
    unittest.main()
