import json
import re
from concurrent.futures import ThreadPoolExecutor
from html import escape
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import ui

from .core import WebSpanCore


_SCHEME = "webspan"


class PythonistaWebSpan(WebSpanCore):
    def __init__(self, webview, max_workers=4):
        super().__init__()

        self.webview = webview
        self.webview.delegate = self

        self._executor = ThreadPoolExecutor(
            max_workers=max_workers
        )
        self._closed = False

        self._webspan_js = self._load_webspan_js()

    def close(self):
        if self._closed:
            return

        self._closed = True
        self._executor.shutdown(
            wait=False,
            cancel_futures=True,
        )

    def _load_webspan_js(self):
        path = (
            Path(__file__).parent
            / "static"
            / "webspan.js"
        )

        return path.read_text(encoding="utf-8")

    # ---------- HTML ----------

    def load_html(self, path: str | Path) -> None:
        path = Path(path).expanduser().resolve()
        html = path.read_text(encoding="utf-8")
        html = self._inject_base_url(
            html,
            path.parent.as_uri() + "/",
        )
        html = self._inject_webspan(html)

        self.webview.load_html(html)

    @staticmethod
    def _inject_base_url(html, base_url):
        base = f'<base href="{escape(base_url, quote=True)}">'
        head = re.search(r"<head(?:\s[^>]*)?>", html, re.IGNORECASE)

        if head:
            return html[:head.end()] + "\n" + base + html[head.end():]

        return base + "\n" + html

    def _inject_webspan(self, html):
        script = f"""
<script>
{self._webspan_js}
</script>
"""

        if "</head>" in html:
            return html.replace(
                "</head>",
                script + "\n</head>",
                1,
            )

        return script + html

    # ---------- WebView Delegate ----------

    def webview_should_start_load(
        self,
        webview,
        url,
        nav_type,
    ):
        parsed = urlparse(url)

        # 普通 http/file/about 等请求正常放行
        if parsed.scheme != _SCHEME:
            return True

        # webspan://call?... 才是我们的 RPC
        if parsed.netloc != "call":
            return False

        try:
            request = self._parse_request(parsed)
        except Exception as exc:
            # 如果连 request id 都解析不出来，
            # JS 那边也没办法对应 Promise
            print("webspan malformed request:", exc)
            return False

        self._run_request(request)

        # 阻止 WebView 真正导航到这个 URL
        return False

    # ---------- Request ----------

    def _parse_request(self, parsed):
        query = parse_qs(
            parsed.query,
            keep_blank_values=True,
        )

        request_id = self._require_param(query, "id")
        method = self._require_param(query, "method")

        raw_data = query.get("data", ["null"])[0]

        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON payload") from exc

        return {
            "id": request_id,
            "method": method,
            "data": data,
        }

    @staticmethod
    def _require_param(query, name):
        values = query.get(name)

        if not values:
            raise ValueError(
                f"Missing request parameter: {name}"
            )

        return values[0]

    # ---------- Dispatch ----------

    def _run_request(self, request):
        if self._closed:
            return

        self._executor.submit(
            self._handle_request,
            request
        )

    def _handle_request(self, request):
        request_id = request["id"]

        try:
            result = self.dispatch(
                request["method"],
                request["data"],
            )

            response = {
                "ok": True,
                "result": result,
            }

        except Exception as exc:
            response = {
                "ok": False,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            }

        self._send_response(
            request_id,
            response,
        )

    # ---------- Python -> JavaScript ----------

    def _send_response(self, request_id, response):
        request_json = json.dumps(
            request_id,
            ensure_ascii=False,
        )

        response_json = json.dumps(
            response,
            ensure_ascii=False,
        )

        js = (
            "window.webspan._resolve("
            f"{request_json},"
            f"{response_json}"
            ");"
        )

        # eval_js 必须回 UI thread
        ui.delay(
            lambda: self.webview.eval_js(js),
            0,
        )
