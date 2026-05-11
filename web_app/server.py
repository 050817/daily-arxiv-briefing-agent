from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
    BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    BUNDLE_ROOT = PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from agent.io_utils import ensure_dir, load_config, load_json, resolve_path, save_json
from agent.openai_compat import has_openai_compatible_api_key, load_openai_compatible_settings, resolve_openai_compatible_config
from agent.orchestrator import DailyArxivBriefingAgent
from skills.briefing_graph.skill import BriefingGraphSkill


STATIC_DIR = BUNDLE_ROOT / "web_app" / "static"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".pdf": "application/pdf",
    ".svg": "image/svg+xml",
}


class BriefingWebApp:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.paths = self.config.get("paths", {})
        self.archive_dir = resolve_path(self.paths.get("archive_dir", "archives"))
        self.briefing_skill = BriefingGraphSkill(self.config)

    def get_settings(self) -> dict[str, Any]:
        settings = load_openai_compatible_settings()
        resolved = resolve_openai_compatible_config(default_model="gpt-5.4")
        return {
            "api_url": settings.get("api_url") or resolved["api_url"],
            "model": settings.get("model") or resolved["model"],
            "api_key": settings.get("api_key", ""),
            "has_api_key": has_openai_compatible_api_key(),
        }

    def save_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        api_url = str(payload.get("api_url", "")).strip()
        model = str(payload.get("model", "")).strip() or "gpt-5.4"
        api_key = str(payload.get("api_key", "")).strip()
        current = load_openai_compatible_settings()
        if not api_key and current.get("api_key"):
            api_key = current["api_key"]
        settings = {"api_url": api_url, "model": model, "api_key": api_key}
        settings_path = resolve_path("web_app/local_settings.json")
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.get_settings()

    def run_workflow(self, payload: dict[str, Any]) -> dict[str, Any]:
        query = str(payload.get("query", "")).strip()
        if not query:
            raise ValueError("query is required")
        user_input = {
            "query": query,
            "date_range": str(payload.get("date_range", "all") or "all"),
            "max_results": int(payload.get("max_results", 10) or 10),
            "top_k": int(payload.get("top_k", 5) or 5),
            "method": str(payload.get("method", "tfidf") or "tfidf"),
        }
        agent = DailyArxivBriefingAgent(self.config_path)
        result = agent.run(user_input)
        archive = self._archive_latest_run(query, result, user_input)
        return {"workflow": result, "archive": archive}

    def list_archives(self) -> list[dict[str, Any]]:
        if not self.archive_dir.exists():
            return []
        archives = []
        for path in sorted(self.archive_dir.iterdir(), reverse=True):
            if not path.is_dir():
                continue
            metadata_path = path / "metadata.json"
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            else:
                metadata = {"id": path.name, "query": path.name, "files": {}}
            metadata["path"] = str(path)
            archives.append(metadata)
        return archives

    def get_archive(self, archive_id: str) -> dict[str, Any]:
        archive_path = self._safe_archive_path(archive_id)
        metadata = load_json(archive_path / "metadata.json")
        chat_path = archive_path / "chat.json"
        chat = load_json(chat_path) if chat_path.exists() else {"messages": []}
        return {"metadata": metadata, "chat": chat}

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        archive_id = str(payload.get("archive_id", "")).strip()
        message = str(payload.get("message", "")).strip()
        if not archive_id:
            raise ValueError("archive_id is required")
        if not message:
            raise ValueError("message is required")

        archive_path = self._safe_archive_path(archive_id)
        context = self._load_archive_context(archive_path)
        answer = self._call_model_or_fallback(message, context)
        chat_path = archive_path / "chat.json"
        chat = load_json(chat_path) if chat_path.exists() else {"messages": []}
        chat["messages"].extend(
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": answer},
            ]
        )
        save_json(chat, chat_path)
        return {"answer": answer, "messages": chat["messages"]}

    def _archive_latest_run(self, query: str, result: dict[str, Any], user_input: dict[str, Any]) -> dict[str, Any]:
        briefing = result.get("outputs", {}).get("briefing", {})
        figures = list(briefing.get("figures", []))
        artifacts = {
            "report_markdown": briefing.get("report_markdown") or self.paths.get("report", "outputs/reports/daily_briefing.md"),
            "report_pdf": briefing.get("report_pdf") or self.paths.get("report_pdf", "outputs/reports/daily_briefing.pdf"),
            "keyword_graph": figures[0] if len(figures) > 0 else "",
            "top_keywords": figures[1] if len(figures) > 1 else "",
            "raw_papers": self.paths.get("raw_papers", "data/raw/arxiv_papers.json"),
            "ranked_papers": self.paths.get("ranked_papers", "data/processed/ranked_papers.json"),
        }
        date_metadata = self._date_range_metadata(str(user_input.get("date_range", "all")))
        return self.briefing_skill.archive_outputs(
            query,
            artifacts,
            archive_dir=str(self.archive_dir),
            metadata_extra={
                "date_range": user_input.get("date_range", "all"),
                **date_metadata,
                "display_title": self._archive_display_title(query, date_metadata),
            },
        )

    def _date_range_metadata(self, date_range: str) -> dict[str, str]:
        value = date_range.strip().lower()
        today = datetime.now().date()
        if value in {"", "all", "any", "*"}:
            return {"date_start": "all", "date_end": "all", "date_label": "全部时间"}
        if value == "today":
            return {"date_start": today.isoformat(), "date_end": today.isoformat(), "date_label": today.isoformat()}
        if value == "yesterday":
            yesterday = today - timedelta(days=1)
            return {
                "date_start": yesterday.isoformat(),
                "date_end": yesterday.isoformat(),
                "date_label": yesterday.isoformat(),
            }
        match = __import__("re").fullmatch(r"last\s+(\d+)\s+days?", value)
        if match:
            days = max(1, int(match.group(1)))
            start = today - timedelta(days=days - 1)
            return {
                "date_start": start.isoformat(),
                "date_end": today.isoformat(),
                "date_label": f"{start.isoformat()} 至 {today.isoformat()}",
            }
        return {"date_start": value, "date_end": value, "date_label": value}

    def _archive_display_title(self, query: str, date_metadata: dict[str, str]) -> str:
        return f"{query} | {date_metadata.get('date_label', 'unknown dates')}"

    def _safe_archive_path(self, archive_id: str) -> Path:
        root = ensure_dir(self.archive_dir).resolve()
        candidate = (root / archive_id).resolve()
        if root not in candidate.parents and candidate != root:
            raise ValueError("invalid archive id")
        if not candidate.exists() or not candidate.is_dir():
            raise FileNotFoundError("archive not found")
        return candidate

    def _load_archive_context(self, archive_path: Path) -> str:
        chunks = []
        for name in ["metadata.json", "report.md", "ranked_papers.json", "raw_papers.json"]:
            path = archive_path / name
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="replace")
                chunks.append(f"[{name}]\n{text[:12000]}")
        return "\n\n".join(chunks)

    def _call_model_or_fallback(self, message: str, context: str) -> str:
        settings = load_openai_compatible_settings()
        api_key = resolve_openai_compatible_config(default_model="gpt-5.4").get("api_key", "")
        if api_key:
            try:
                return self._call_openai_compatible_model(message, context, api_key, settings)
            except Exception as exc:
                return (
                    "模型接口调用失败，下面给出基于归档文件的本地回答。\n\n"
                    f"接口错误: {exc}\n\n{self._fallback_answer(message, context)}"
                )
        return self._fallback_answer(message, context)

    def _call_openai_compatible_model(
        self,
        message: str,
        context: str,
        api_key: str,
        settings: dict[str, Any],
    ) -> str:
        resolved = resolve_openai_compatible_config(
            configured_base_url=str(settings.get("api_url", "")).strip(),
            configured_model=str(settings.get("model", "")).strip(),
            configured_api_key=api_key,
            default_model="gpt-4.1-mini",
        )
        base_url = resolved["api_url"].rstrip("/")
        model = resolved["model"]
        request_body = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You answer questions about an archived arXiv briefing. "
                        "Use only the provided report/archive context. If the answer is not in the files, say so."
                    ),
                },
                {"role": "user", "content": f"Archive context:\n{context[:30000]}\n\nQuestion: {message}"},
            ],
        }
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(request_body).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def _fallback_answer(self, message: str, context: str) -> str:
        terms = [term.lower() for term in message.split() if len(term) > 2]
        lines = [line.strip() for line in context.splitlines() if line.strip()]
        matches = [
            line for line in lines if any(term in line.lower() for term in terms)
        ][:8]
        if not matches:
            matches = lines[:8]
        evidence = "\n".join(f"- {line[:420]}" for line in matches)
        return (
            "当前未配置模型 API key，因此我使用归档文件做本地检索式回答。\n\n"
            f"相关文件片段:\n{evidence}\n\n"
            "如果需要真正的模型对话，请在启动服务前设置 OPENAI_API_KEY；可选设置 OPENAI_BASE_URL 和 OPENAI_MODEL。"
        )


APP = BriefingWebApp()


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        try:
            if self.path == "/" or self.path.startswith("/static/"):
                self._serve_static()
            elif self.path == "/api/settings":
                self._send_json(APP.get_settings())
            elif self.path == "/api/archives":
                self._send_json({"archives": APP.list_archives()})
            elif self.path.startswith("/api/archives/"):
                self._serve_archive_get()
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._send_error(exc)

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            if self.path == "/api/run":
                self._send_json(APP.run_workflow(payload))
            elif self.path == "/api/settings":
                self._send_json(APP.save_settings(payload))
            elif self.path == "/api/chat":
                self._send_json(APP.chat(payload))
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._send_error(exc)

    def _serve_static(self) -> None:
        if self.path == "/":
            path = STATIC_DIR / "index.html"
        else:
            relative = self.path[len("/static/") :].split("?", 1)[0]
            path = (STATIC_DIR / relative).resolve()
            try:
                path.relative_to(STATIC_DIR.resolve())
            except ValueError:
                self.send_error(HTTPStatus.FORBIDDEN)
                return
        self._serve_file(path)

    def _serve_archive_get(self) -> None:
        parts = self.path.split("/")
        archive_id = parts[3] if len(parts) > 3 else ""
        if len(parts) == 4:
            self._send_json(APP.get_archive(archive_id))
            return
        if len(parts) >= 6 and parts[4] == "file":
            archive_path = APP._safe_archive_path(archive_id)
            filename = "/".join(parts[5:]).split("?", 1)[0]
            path = (archive_path / filename).resolve()
            try:
                path.relative_to(archive_path.resolve())
            except ValueError:
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            self._serve_file(path)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _serve_file(self, path: Path) -> None:
        if not path.exists() or path.is_dir():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send_json(self, data: dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, exc: Exception) -> None:
        status = HTTPStatus.NOT_FOUND if isinstance(exc, FileNotFoundError) else HTTPStatus.BAD_REQUEST
        body = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[web] {self.address_string()} - {format % args}")


def main() -> None:
    port = int(os.environ.get("ARXIV_WEB_PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), RequestHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"Daily arXiv web app running at {url}")
    if os.environ.get("ARXIV_WEB_NO_BROWSER", "").lower() not in {"1", "true", "yes"}:
        webbrowser.open(url)
    server.serve_forever()


if __name__ == "__main__":
    main()
