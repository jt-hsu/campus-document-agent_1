# 文件智慧問答 AI Agent

使用 Python、Document Search Tool 與 Ollama / Qwen3-4B 建立校園規章問答系統。Agent 先搜尋預先整理的國立臺北大學規章，找到相關條文後才交由模型整理回答；若查無依據，則提示無法確認。Agent 與搜尋工具使用 **Podman** 容器執行，Ollama Server 位於容器外。

> 課程示範專案：收錄文件不保證為校方現行最新版，回答不能取代校方正式解釋。

## 1. 系統需求

- **Podman**：容器建置與執行（Windows 使用 Podman Machine / WSL2）
- **Ollama**：需能從容器連線的 LLM Server
- **模型**：`qwen3:4b`（可由 `OLLAMA_MODEL` 修改）
- **Python 3.11**：僅供本機開發；容器會自行提供 Python 環境

本專案目前的 Python 程式使用標準函式庫，無須額外安裝 pip 套件。模型權重不包含在 Repository 或 Podman Image 內。

## 2. 專案結構

```text
.
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

`documents/index.json` 已包含三份公開規章整理出的 40 個條文區塊，執行時不需重新解析 PDF。

## 3. 準備 Ollama

先[安裝 Ollama](https://ollama.com/download)，然後在 Windows PowerShell 執行：

```powershell
ollama pull qwen3:4b
ollama list
curl.exe http://127.0.0.1:11434/api/tags
```

最後一行若回傳模型清單 JSON，表示 **Windows 本機**的 Ollama API 正常；容器連線仍需另外確認。

## 4. 使用 Podman 執行（建議）

在包含 `Containerfile` 的**專案根目錄**，使用 PowerShell 執行。

### 4.1 啟動 Podman Machine

```powershell
podman machine list
```

若已建立 Machine 但尚未運行，執行 `podman machine start`；若尚未建立，先執行 `podman machine init`，再執行 `podman machine start`。

### 4.2 建置 Image

```powershell
podman build -t campus-agent-hw2 -f Containerfile .
```

### 4.3 測試容器到 Ollama 的連線

```powershell
podman run --rm campus-agent-hw2 python -c "import urllib.request; print(urllib.request.urlopen('http://host.containers.internal:11434/api/tags', timeout=8).status)"
```

顯示 `200` 表示容器能連到 Ollama API。`host.containers.internal` 的可用性視 Podman／作業系統網路配置而定。

### 4.4 啟動 Agent

```powershell
podman run --rm -e OLLAMA_URL=http://host.containers.internal:11434 -e OLLAMA_MODEL=qwen3:4b campus-agent-hw2 python src/main.py "銷過之後操行分數會恢復嗎？" --trace
```

若要互動輸入問題：

```powershell
podman run --rm -it -e OLLAMA_URL=http://host.containers.internal:11434 campus-agent-hw2 python src/main.py --trace
```

輸入 `exit` 或 `quit` 結束互動模式。`--trace` 顯示 Agent 決策及工具執行紀錄；`--json` 輸出完整 JSON。

## 5. 測試

不需啟動 Ollama，即可在容器內執行自動化測試：

```powershell
podman run --rm campus-agent-hw2 python -m unittest discover -s tests -v
```

預期顯示 `Ran 14 tests ... OK`。這些是搜尋工具與 Agent Workflow 的單元測試，其中 Agent 測試使用模擬 LLM，並不代表真實模型的回答準確率。

亦可測試文件外問題的拒答行為：

```powershell
podman run --rm campus-agent-hw2 python src/main.py "學校咖啡廳珍珠奶茶多少錢？" --trace
```

預期回傳 `[no_result]`。

## 6. 本機開發（選用）

不使用 Podman 時，可在 Windows PowerShell 建立虛擬環境後直接執行：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python src/main.py "銷過之後操行分數會恢復嗎？" --trace
python -m unittest discover -s tests -v
```

此方式的預設 Ollama URL 為 `http://localhost:11434`。

## 7. 常見問題

- **`llm_connection_error` / `timed out`**：確認 Ollama 已啟動、模型已下載、容器可連到設定的 `OLLAMA_URL`，再檢查 Windows 防火牆和 Podman Machine 網路。
- **Ollama 只監聽 `127.0.0.1`**：可依網路環境調整 `OLLAMA_HOST`，但不要將無驗證的 11434 API 公開到網際網路；只允許受信任的連線。
- **`no_result`**：收錄規章無符合檢索門檻的段落，系統不會要求模型猜測。

Agent 設計、檢索判定標準、測試分析與 Failure Cases 請參考 `reports/` 內的 HW2 技術報告。
