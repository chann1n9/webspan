# WebSpan

WebSpan connects HTML and JavaScript interfaces to Python running in
[Pythonista](https://omz-software.com/pythonista/). It adds a small asynchronous
bridge to `ui.WebView`: JavaScript calls explicitly registered Python handlers,
then receives their results through Promises.

Use HTML, CSS, and JavaScript for the interface while keeping networking,
storage, and Pythonista-specific capabilities in Python. WebSpan has no
third-party runtime dependencies and requires Python 3.10 or newer.

[Releases](https://github.com/chann1n9/webspan/releases) ·
[Complete sample](Sample/)

## Installation

Run the following code in Pythonista to install the latest release, then restart
Pythonista:

```python
exec(compile(__import__("requests").get("https://raw.githubusercontent.com/chann1n9/webspan/refs/heads/main/install.py", timeout=15).text, "webspan_install.py", "exec"))
```

## Usage

Keep the HTML file and any relative assets, such as stylesheets or images,
together.

```python
# app.py
from pathlib import Path

import ui

from webspan import PythonistaWebSpan


def greet(data):
    name = data.get("name", "there")
    return {"message": f"Hello, {name}!"}


def main():
    webview = ui.WebView()
    span = PythonistaWebSpan(webview)

    try:
        span.register("greet", greet)
        span.load_html(Path(__file__).with_name("index.html"))

        webview.present("fullscreen")
        webview.wait_modal()
    finally:
        span.close()


if __name__ == "__main__":
    main()
```

Call the registered handler from the page:

```html
<!-- index.html -->
<button id="greet">Greet</button>
<p id="result"></p>

<script>
const result = document.querySelector("#result")

document.querySelector("#greet").addEventListener("click", async () => {
    try {
        const response = await webspan.call("greet", { name: "WebSpan" })
        result.textContent = response.message
    } catch (error) {
        result.textContent = `${error.name}: ${error.message}`
    }
})
</script>
```

`span.load_html()` takes a file path and injects both the WebSpan JavaScript API
and a base URL for relative assets; the page does not need to include
`webspan.js` itself. Each `webspan.call()` accepts an optional JSON-serializable
payload; the handler receives that one value (`None` when it is omitted), and
its return value must also be JSON-serializable. A Python exception rejects the
JavaScript Promise with the exception type and message.

Handlers run on background worker threads. If a handler needs to update a
native Pythonista view, schedule that work on the UI thread. Always call
`span.close()` when the WebView is dismissed so worker and debug resources are
released.

See [`Sample/sample.py`](Sample/sample.py) and
[`Sample/index.html`](Sample/index.html) for a complete working example.

## Desktop debugging with Toga

Pythonista's `ui` module is unavailable in a regular desktop Python
interpreter. For desktop debugging, WebSpan therefore includes a small
[Toga](https://toga.readthedocs.io/) adapter that implements the subset of
`ui.WebView` needed by the bridge. Toga provides a real WebView, navigation
hooks, JavaScript evaluation, and a GUI event loop, so the same HTML-to-Python
calls can be exercised outside Pythonista. The adapter also serves relative
assets from a temporary loopback HTTP server for desktop WebView compatibility.

Change the `ui` import in your application's entry point as follows:

```python
import os

if os.environ.get("WEBSPAN_DEBUG") == "1":
    from webspan.debug.toga import ui
else:
    import ui
```

The rest of the application can continue to use `ui.WebView()` unchanged. From
a source checkout, install the development dependencies and enable the desktop
adapter when launching the script:

```sh
uv sync
WEBSPAN_DEBUG=1 uv run python Sample/sample.py
```

`WEBSPAN_DEBUG` is read by the conditional import above, not by WebSpan itself.
Apply the same import strategy in any other module that imports Pythonista's
`ui` directly.

Toga is a development-only dependency and is not needed in Pythonista. Its
adapter is intentionally limited to the `ui.WebView` behavior WebSpan uses; it
does not emulate the full Pythonista `ui` module. Desktop mode is suitable for
debugging the web interface, handlers, and bridge, but final platform behavior
should still be verified in Pythonista.
