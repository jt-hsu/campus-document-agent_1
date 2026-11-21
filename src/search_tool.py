"""Campus Document Search Tool (HW2 的第一個可執行元件)。

採固定詞組比對作為最小雛形；使用查詢關鍵字覆蓋率評分。
這不是完整的中文斷詞系統，分詞與同義詞擴充可留給 HW3。
"""
import json
import sys
from pathlib import Path

DEFAULT_INDEX = Path(__file__).resolve().parents[1] / "documents" / "index.json"

# 同一組關鍵字可有不同的常見說法。左側是 canonical term。
# 這是規則式最小範例，不是語意搜尋，也不保證辨識所有改寫。
ALIASES = {
    "病假": ["病假", "因病", "生病"],
    "請假": ["請假", "請一天假", "請幾天假"],
    "心理假": ["心理假", "心理不適"],
    "生理假": ["生理假", "生理期"],
    "公假": ["公假"],
    "事假": ["事假", "重大事故"],
    "喪假": ["喪假", "喪故"],
    "超過三日": ["超過三日", "超過三天", "三日以上", "三天以上", "逾三日", "逾三日以上"],
    "證明": ["證明", "檢附", "檢具", "診斷書"],
    "期限": ["期限", "幾天內", "多久", "逾期"],
    "學期": ["學期"],
    "獎勵": ["獎勵", "嘉獎", "記功", "小功", "大功"],
    "懲處": ["懲處", "處分", "懲罰"],
    "考試舞弊": ["考試舞弊", "考試作弊", "作弊"],
    "大過": ["大過"],
    "小過": ["小過"],
    "申誡": ["申誡"],
    "扣分": ["扣分", "扣減", "扣操行", "扣操行總分"],
    "操行": ["操行"],
    "退學": ["退學"],
    "開除": ["開除學籍", "開除"],
    "宿舍": ["宿舍", "住宿"],
    "申訴": ["申訴"],
    "銷過": ["銷過", "消過", "註銷"],
    "抵銷": ["抵銷", "抵消", "抵過"],
    "假別": ["假別", "種類", "哪些假"],
}


def extract_query_terms(query: str) -> list[str]:
    """抽取查詢中出現的領域關鍵字。先匹配長詞以降低重疊。"""
    query = query.replace(" ", "").strip()
    hits = []
    for canonical, variants in ALIASES.items():
        if any(v in query for v in variants):
            hits.append(canonical)
    # 更具體的詞存在時，略過容易造成噪音的一般詞。
    if any(t in hits for t in ("病假", "心理假", "生理假", "公假", "事假", "喪假")):
        hits = [x for x in hits if x != "請假"]
    return hits


def match_term(term: str, text: str) -> bool:
    return any(variant in text for variant in ALIASES[term])


def search_documents(query: str, top_k: int = 3,
                     threshold: float = 0.5, index_path=DEFAULT_INDEX) -> dict:
    """回傳 status / decision inputs / ranked evidence。

    Score = matching query terms / all extracted query terms.
    檢索相關性不等於證據充足，後續 Agent 仍需判定可否回答。
    """
    if not isinstance(query, str) or not query.strip():
        return {"status": "error", "reason": "empty_query", "results": []}
    if top_k < 1 or not (0 <= threshold <= 1):
        return {"status": "error", "reason": "invalid_parameters", "results": []}
    try:
        data = json.loads(Path(index_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"status": "error", "reason": "index_unavailable", "detail": str(exc), "results": []}
    keywords = extract_query_terms(query)
    if not keywords:
        return {"status": "no_result", "reason": "no_recognized_keywords", "query_keywords": [], "results": []}

    matches = []
    for sec in data["sections"]:
        matched = [term for term in keywords if match_term(term, sec["content"])]
        score = round(len(matched) / len(keywords), 3)
        if matched and score >= threshold:
            matches.append({
                "document": sec["document"], "article": sec["article"],
                "page": sec["page"], "version": sec["version"],
                "source_pdf": sec["source_pdf"],
                "content": sec["content"], "matched_keywords": matched,
                "score": score,
            })
    matches.sort(key=lambda v: (-v["score"], -len(v["matched_keywords"]),len(v["content"])))
    results = matches[:top_k]
    return {"status": "success" if results else "no_result", "query_keywords": keywords,
            "threshold": threshold, "top_k": top_k, "results": results}


if __name__ == "__main__":
    user_query = " ".join(sys.argv[1:]).strip() or input("請輸入校園規章問題：").strip()
    print(json.dumps(search_documents(user_query), ensure_ascii=False, indent=2))
