import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from search_tool import search_documents

class DocumentSearchTests(unittest.TestCase):
    def test_sick_leave(self):
        result = search_documents("病假超過三天需要哪些證明？")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["results"][0]["article"], "第四條")
        self.assertEqual(result["results"][0]["document"], "國立臺北大學學生請假規定")

    def test_psychological_leave(self):
        result = search_documents("心理假一學期能請幾天？")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["results"][0]["article"], "第七條")

    def test_exam_cheating(self):
        result = search_documents("考試作弊會記大過嗎？")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["results"][0]["article"], "第十二條")
        self.assertEqual(result["results"][0]["document"], "國立臺北大學學生獎懲辦法")

    def test_demerit_cancellation_score(self):
        result = search_documents("銷過之後操行分數會恢復嗎？")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["results"][0]["document"], "國立臺北大學學生銷過實施要點")
        self.assertEqual(result["results"][0]["article"], "第四條")

    def test_demerit_cancellation_rules(self):
        result = search_documents("銷過可以用之前的獎勵抵銷嗎？")
        self.assertEqual(result["status"], "success")
        self.assertTrue(any(r["document"] == "國立臺北大學學生銷過實施要點" and r["article"] == "第三條" for r in result["results"]))

    def test_no_result(self):
        result = search_documents("請問校園咖啡廳的珍珠奶茶多少錢？")
        self.assertEqual(result["status"], "no_result")

    def test_empty(self):
        result = search_documents("  ")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason"], "empty_query")

if __name__ == "__main__":
    unittest.main()
