"""Use Ollama's local /api/chat API. Standard-library only."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMConnectionError(RuntimeError):
    """Ollama did not respond or returned an HTTP error."""


class LLMResponseError(RuntimeError):
    """Ollama returned unusable data."""


SYSTEM_PROMPT = """你是大學校園規章文件問答助手。你只能根據使用者提供的【文件證據】回答，不使用外部常識推測校規。
請仔細區分「字詞相關」和「有足夠證據」。如果證據不足、或需要行政單位裁量才有答案，回答不可確認。
對日期、期限、條件、例外與資格等資訊，不得擴大解釋；保留原文限制條件。
文件可能有不同版本；不要自行將舊版本條號當成新版條號，也不要聲稱文件一定是現行有效版本。
只回傳一個 JSON 物件，不要 Markdown、不附帶其他文字：
{"supported": true或false, "answer": "繁體中文簡要回答；證據不足時說明無法從目前文件確認", "evidence_ids": ["E1"]}
若 supported 為 true，evidence_ids 至少一個，且只能使用提供的證據編號。若為 false，evidence_ids 必須是空陣列。
"""


def chat_with_ollama(question: str, evidence: list[dict], *, base_url: str | None = None,
                     model: str | None = None, timeout: float = 90.0) -> dict:
    """Return {supported, answer, evidence_ids}; errors are typed exceptions."""
    base_url = (base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
    model = model or os.getenv("OLLAMA_MODEL", "qwen3:4b")

    lines = [f"使用者問題：{question}", "\n【文件證據】"]
    for i, item in enumerate(evidence, start=1):
        lines.append(f"E{i} | {item['document']} | {item['article']} | 頁 {item['page']} | 版本：{item['version']}\n{item['content']}")
    body = {
        "model": model,
        "stream": False,
        "think": False,
        "format": "json",
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "\n\n".join(lines)},
        ],
    }
    req = Request(base_url + "/api/chat", data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise LLMConnectionError(f"Ollama HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise LLMConnectionError(f"無法連線 Ollama（{base_url}）：{exc}") from exc
    try:
        data = json.loads(raw)
        text = data["message"]["content"]
        parsed = json.loads(text)
        if not isinstance(parsed, dict) or type(parsed.get("supported")) is not bool:
            raise ValueError("supported 必須是布林值")
        if not isinstance(parsed.get("answer"), str) or not parsed["answer"].strip():
            raise ValueError("answer 缺少非空字串")
        if not isinstance(parsed.get("evidence_ids"), list) or not all(
            isinstance(x, str) for x in parsed["evidence_ids"]
        ):
            raise ValueError("evidence_ids 必須是字串陣列")
        return parsed
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise LLMResponseError(f"Ollama 回傳內容無法解析：{exc}") from exc
