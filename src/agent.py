"""Single-Agent, Tool Use + State-based Decision workflow.

Search relevance and answer sufficiency are separate stages.
"""
from llm_client import chat_with_ollama, LLMConnectionError, LLMResponseError
from search_tool import search_documents


def run_agent(question: str, *, search_fn=search_documents, llm_fn=chat_with_ollama) -> dict:
    trace = [{"step": "User Input", "detail": question}]
    if not isinstance(question, str) or not question.strip():
        trace.append({"step": "Agent Decision", "detail": "empty_query：拒絕空白輸入"})
        return {"status": "invalid_input", "answer": "請輸入有效的校園規章問題。", "sources": [], "trace": trace}

    trace.append({"step": "Agent Decision", "detail": "輸入有效，呼叫 Document Search Tool"})
    trace.append({"step": "Tool Call", "tool": "search_documents", "input": {"query": question, "top_k": 3, "threshold": 0.5}})
    search = search_fn(question, top_k=3, threshold=0.5)
    trace.append({"step": "Observation", "status": search.get("status"),
                  "query_keywords": search.get("query_keywords", []),
                  "results": [
                      {"id": f"E{i}", "document": item["document"], "article": item["article"], "score": item["score"]}
                      for i, item in enumerate(search.get("results", []), start=1)
                  ]})

    if search.get("status") == "error":
        trace.append({"step": "Agent Decision", "detail": "Tool 失敗，停止執行並回報錯誤"})
        return {"status": "tool_error", "answer": "文件搜尋工具發生錯誤，無法完成查詢。",
                "detail": search.get("reason"), "sources": [], "trace": trace}
    if search.get("status") != "success" or not search.get("results"):
        trace.append({"step": "Agent Decision", "detail": "無符合門檻的候選段落，不呼叫 LLM"})
        return {"status": "no_result", "answer": "目前收錄的文件找不到足夠相關的段落，無法確認答案。",
                "sources": [], "trace": trace}

    evidence = search["results"]
    trace.append({"step": "Agent Decision", "detail": f"取得 {len(evidence)} 筆候選段落，呼叫 Ollama 判定證據是否足夠"})
    try:
        result = llm_fn(question, evidence)
    except LLMConnectionError as exc:
        trace.append({"step": "Observation", "detail": "LLM 連線失敗"})
        return {"status": "llm_connection_error", "answer": "目前無法連線至 Ollama，請確認服務已啟動。",
                "detail": str(exc), "sources": [], "trace": trace}
    except LLMResponseError as exc:
        trace.append({"step": "Observation", "detail": "LLM 回覆格式無法解析"})
        return {"status": "llm_response_error", "answer": "LLM 回傳格式異常，無法產生可信的回答。",
                "detail": str(exc), "sources": [], "trace": trace}

    valid_ids = {f"E{i}": item for i, item in enumerate(evidence, start=1)}
    selected = list(dict.fromkeys(result.get("evidence_ids", [])))
    # This check validates evidence IDs/format, not the semantic truth of the LLM's answer.
    if result.get("supported") is not True:
        trace.append({"step": "Agent Decision", "detail": "LLM 判定證據不足，拒答"})
        return {"status": "insufficient_evidence", "answer": "目前檢索到的段落不足以確認答案。",
                "sources": [], "trace": trace}
    if not selected or any(identifier not in valid_ids for identifier in selected):
        trace.append({"step": "Agent Decision", "detail": "LLM 引用的證據編號無效，拒絕輸出"})
        return {"status": "invalid_evidence_ids", "answer": "回答未能對應有效來源，無法確認答案。",
                "sources": [], "trace": trace}

    sources = [{"id": identifier, **{k: valid_ids[identifier][k] for k in
        ("document", "article", "page", "version", "source_pdf", "score")}} for identifier in selected]
    trace.append({"step": "Final Decision", "detail": "已取得回答與有效的證據編號；來源已附上（尚未驗證語意正確性）"})
    return {"status": "answered", "answer": result["answer"], "sources": sources,
            "trace": trace, "disclaimer": "本回答僅依收錄文件，非校方正式解釋；各文件現行效力尚未確認。"}
