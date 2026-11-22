# 文件智慧問答 AI Agent

本專案使用 Python、Document Search Tool、State-based Decision 與 Ollama / Qwen3-4B，建立國立臺北大學校園規章問答系統。

Agent 先搜尋預先整理的規章條文，篩選符合相關性門檻的候選段落，再由 LLM 判斷證據是否足夠並整理回答；若找不到相關內容，則回覆無法確認。Agent 與搜尋工具透過 Podman 容器執行，Ollama LLM Server 位於容器外。

> 本專案為課堂作業示範系統。收錄文件不保證為校方現行最新版，回答僅供查詢參考，不取代校方正式公告或行政單位解釋。

## 1. 系統需求

- Podman：負責建置與執行 Agent 容器。Windows 需有可運作的 Podman Machine（WSL2 或其他支援的 Provider）。
- Ollama：提供容器可以連線的 LLM API Server。
- 模型：`qwen3:4b`，可透過 `OLLAMA_MODEL` 環境變數調整。
- Python 3.11：容器映像內已包含；只有在不使用 Podman、直接於本機開發時才需另行安裝。

目前執行階段的 Python 程式只使用標準函式庫，沒有額外的 pip 套件依賴；因此 `requirements.txt` 只有說明註解。Ollama 與模型權重不包含在 GitHub Repository 或 Podman Image 中。

## 2. 專案結構與資料來源

```text
.
├── README.md
├── Containerfile
├── requirements.txt
├── documents/
│   ├── index.json
│   └── source_pdfs/
├── src/
│   ├── main.py
│   ├── agent.py
│   ├── search_tool.py
│   └── llm_client.py
├── tests/
│   ├── test_agent.py
│   └── test_search.py
└── reports/
```

| 收錄文件                    | PDF 記載版本              | 索引區塊數         |
|----------------------------|--------------------------|------------------:|
| 國立臺北大學學生請假規定     | 113 年 4 月 16 日校長核定  | 13                |
| 國立臺北大學學生獎懲辦法     | 111 年 11 月 16 日修正通過 | 22（含第七條之一） |
| 國立臺北大學學生銷過實施要點 | 101 年 4 月 12 日發布      | 5                 |

`documents/index.json` 收錄以上 3 份公開文件、40 個以條文為單位的索引區塊；執行 Agent 時不必重新解析 PDF。

文件版本限制： 101 年版《學生銷過實施要點》第一條引用《學生獎懲辦法》第十四條；收錄的 111 年版《學生獎懲辦法》則在第十七條規範銷過。此處保留原文，不自動修正或推定最新有效條文。

## 3. 準備 Ollama（執行完整問答的前置條件）

先至 [Ollama 官方網站](https://ollama.com/download) 安裝 Ollama，並在 Windows PowerShell 執行：

```powershell
ollama pull qwen3:4b
ollama list
curl.exe http://127.0.0.1:11434/api/tags
```

如果最後一行回傳包含 `qwen3:4b` 的模型清單 JSON，代表 Windows 本機的 Ollama API 正常運作；這尚不能證明容器也能連線。

> 若已經有其他可安全存取的 Ollama Server，可以不在執行 Podman 的電腦上安裝 Ollama，但必須透過 `OLLAMA_URL` 指定該服務的位址，且 Server 上須有對應模型。

## 4. 使用 Podman 建置與執行（建議方式）

以下使用 Windows PowerShell。請先進入包含 `Containerfile` 的專案根目錄。

### 4.1 確認 Podman Machine

```powershell
podman --version
podman machine list
podman info
```

若 Machine 已建立但停止，執行 `podman machine start`；若尚未建立，先執行 `podman machine init`，再執行 `podman machine start`。

### 4.2 Build：建立容器映像

```powershell
podman build -t campus-agent-hw2 -f Containerfile .
```

### 4.3 Test：執行容器內單元測試（不需要 Ollama）

```powershell
podman run --rm campus-agent-hw2 python -m unittest discover -s tests -v
```

預期輸出包含 `Ran 14 tests ... OK`，其中搜尋工具 7 項、Agent Workflow 7 項。
Agent 單元測試使用模擬 LLM，不能將 14 項通過視為真實模型回答準確率。

### 4.4 檢查容器與 Ollama 的連線

```powershell
podman run --rm campus-agent-hw2 python -c "import urllib.request; print(urllib.request.urlopen('http://host.containers.internal:11434/api/tags', timeout=8).status)"
```

若顯示 `200`，表示容器可以連到該 Ollama API。Windows 的 `host.containers.internal` 是否可使用，仍取決於 Podman 與主機網路設定。

### 4.5 Run：執行完整 Agent 問答

```powershell
podman run --rm -e OLLAMA_URL=http://host.containers.internal:11434 -e OLLAMA_MODEL=qwen3:4b campus-agent-hw2 python src/main.py "銷過之後操行分數會恢復嗎？" --trace
```

如需連續輸入問題，可使用互動模式：

```powershell
podman run --rm -it -e OLLAMA_URL=http://host.containers.internal:11434 campus-agent-hw2 python src/main.py --trace
```

輸入 `exit` 或 `quit` 結束。`--trace` 會顯示 Agent 的決策與 Tool Call 紀錄；`--json` 可輸出完整 JSON。

預期的成功結果會有 `[answered]`，並包含答案與對應的規章名稱、條號、頁碼及版本。模型輸出仍可能有語意錯誤，引用編號有效不等於內容已經過人工驗證。

## 5. 檢索判定標準與例外處理

Document Search Tool 使用：

```python
search_documents(query, top_k=3, threshold=0.5)
```

- Input：繁體中文查詢問題。
- 檢索策略：以人工整理的 `ALIASES` 關鍵字與常見同義詞比對各條文。
- 相關性分數：`匹配的查詢關鍵字數 / 擷取出的查詢關鍵字總數`。
- 判定門檻：分數 `>= 0.5`，最多回傳分數最高的 3 個候選段落（Top-3）。
- Output：`status`、`query_keywords`、`results` 等，結果包含文件、條號、原文、頁碼、版本、分數。
- 回答判定：無候選段落直接回傳 `no_result`；有候選段落才呼叫 LLM 判斷證據是否足夠，並檢查引用的證據編號是否有效。

> 關鍵限制： 分數代表關鍵字的檢索相關性，不直接代表段落足以回答；LLM 的證據充分性判斷也不等於人工驗證。此為作業 1 回饋「補明檢索判定標準」的對應實作。

可測試文件範圍外的問題：

```powershell
podman run --rm campus-agent-hw2 python src/main.py "學校咖啡廳珍珠奶茶多少錢？" --trace
```

預期回傳 `[no_result]`，Agent 不會要求 LLM 猜測答案。

## 6. 本機開發（選用）

若不使用 Podman，開發者可在 Windows PowerShell 執行：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python src/main.py "銷過之後操行分數會恢復嗎？" --trace
python -m unittest discover -s tests -v
```

本機執行預設連接 `http://localhost:11434` 的 Ollama。若 PowerShell 阻擋啟動虛擬環境，可在該視窗先執行 `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`。

## 7. 常見問題（Troubleshooting）

| 狀況 | 說明與處理 |
|---|---|
| `llm_connection_error` / `timed out` | 確認 Ollama Server 已啟動、`qwen3:4b` 已下載，並依第 4.4 節測試容器連線。再檢查 `OLLAMA_URL`、Podman 網路及防火牆。 |
| Ollama 只監聽 `127.0.0.1` | Podman 可能無法連線。必要時可設定 Windows 使用者環境變數 `OLLAMA_HOST=0.0.0.0:11434` 並重新啟動 Ollama，但應限制私人網路／防火牆存取 |
| `no_result` | 收錄文件沒有符合檢索門檻的候選段落；可能是資料不足，也可能是規則式關鍵字未涵蓋查詢用語。 |
| `llm_response_error` | 模型輸出不是程式可解析的預期 JSON 格式。 |
| `invalid_evidence_ids` | LLM 引用了不存在的候選證據編號，因此 Agent 阻擋該回答。 |

## 8. 已知限制與後續改進

- 本版使用規則式關鍵字檢索，不是 Embedding／向量語意檢索；可能漏掉未收錄的同義詞或間接表達。
- LLM 可依取得的條文整理回答，但不保證每次都正確濃縮、解釋或引用；來源編號檢查也不等於語意正確性檢查。

- HW3：依課程要求建立至少 10 個測試案例，比較 Agent 改進前後的結果與測試指標。
-HW4（視資源與進度）：評估進一步的語意檢索及更自然、精簡的條文解釋。

Agent 架構、測試證據與 Failure Cases 詳見 數位學院 中的 HW2 技術報告。
