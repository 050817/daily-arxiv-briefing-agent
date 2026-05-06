from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent.io_utils import ensure_parent
from agent.orchestrator import DailyArxivBriefingAgent
from agent.schema import STAGES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily arXiv Research Briefing Agent")
    parser.add_argument("--query", type=str, required=True)
    parser.add_argument("--date_range", type=str, default="last 7 days")
    parser.add_argument("--max_results", type=int, default=50)
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--method", type=str, default="tfidf")
    parser.add_argument("--start-at", choices=STAGES, default="retrieval")
    parser.add_argument("--stop-after", choices=STAGES, default="briefing")
    parser.add_argument("--input", dest="input_path", type=str, default=None)
    parser.add_argument("--output-json", type=str, default=None)
    parser.add_argument("--strict", action="store_true", help="Fail instead of stopping cleanly on empty Skills.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    user_input = {
        "query": args.query,
        "date_range": args.date_range,
        "max_results": args.max_results,
        "top_k": args.top_k,
        "method": args.method,
    }

    agent = DailyArxivBriefingAgent()
    result = agent.run(
        user_input,
        start_at=args.start_at,
        stop_after=args.stop_after,
        input_path=args.input_path,
        allow_missing=not args.strict,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.output_json:
        output_path = ensure_parent(args.output_json)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved workflow result to {Path(output_path)}")


if __name__ == "__main__":
    main()
