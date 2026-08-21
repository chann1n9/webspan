import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

if os.environ.get("WEBSPAN_DEBUG") == "1":
    from webspan.debug.toga import ui
else:
    import ui

from webspan import PythonistaWebSpan


HTTPBIN_URL = "https://httpbin.io/get"
REQUEST_TIMEOUT = 15

headers = {
    "Accept": "application/json",
    "User-Agent": "webspan-sample/0.1",
}


def get_httpbin(data):
    request = Request(
        HTTPBIN_URL + "?" + urlencode({"message": data}),
        headers=headers,
    )

    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return json.load(response)["args"]["message"]


def main():
    html_path = Path(__file__).with_name("index.html")

    webview = ui.WebView()
    span = PythonistaWebSpan(webview)
    span.register("getHttpbin", get_httpbin)
    span.load_html(html_path)

    try:
        webview.present("fullscreen")
        webview.wait_modal()
    finally:
        span.close()


if __name__ == "__main__":
    main()
