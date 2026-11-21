"""Command-line interface for campus document QA."""
import argparse
import json
from agent import run_agent


def main():
    parser = argparse.ArgumentParser(description="國立臺北大學校園規章問答 Agent (HW2)")
    parser.add_argument("question", nargs="*", help="規章問題；未指定則進入互動模式")
    parser.add_argument("--trace", action="store_true", help="印出完整 Agent 執行追蹤")
    parser.add_argument("--json", action="store_true", help="輸出機器可讀的完整 JSON")
    args = parser.parse_args()

    if args.question:
        questions = [" ".join(args.question)]
    else:
        print("校園規章 Agent（輸入 exit 離開）")
        questions = None

    while True:
        if questions is not None:
            if not questions:
                break
            q = questions.pop(0)
        else:
            try:
                q = input("問題> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if q.lower() in ("exit", "quit"):
                break
        output = run_agent(q)
        if args.json:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(f"\n[{output['status']}] {output['answer']}")
            for source in output["sources"]:
                print(f"來源：{source['document']} {source['article']}（第{source['page']}頁；版本：{source['version']}）")
            if "detail" in output:
                print(f"錯誤細節：{output['detail']}")
            if "disclaimer" in output:
                print(output["disclaimer"])
            if args.trace:
                print("\n--- Agent Trace ---")
                print(json.dumps(output["trace"], ensure_ascii=False, indent=2))
            print()


if __name__ == "__main__":
    main()
