from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread, current_thread

import toga


_LOOPBACK_HOST = "127.0.0.1"
_IPHONE_PORTRAIT_SIZE = (393, 852)


class _StaticRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        self._root_directory = Path(directory).resolve()
        super().__init__(
            *args,
            directory=str(self._root_directory),
            **kwargs,
        )

    def send_head(self):
        requested_path = Path(
            self.translate_path(self.path)
        ).resolve()

        try:
            requested_path.relative_to(self._root_directory)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return None

        return super().send_head()

    def list_directory(self, path):
        self.send_error(HTTPStatus.NOT_FOUND)
        return None

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format, *args):
        # Keep WebView resource requests out of the debug console.
        pass


class WebView:
    """The small subset of Pythonista's ui.WebView used by WebSpan."""

    def __init__(self):
        self.delegate = None
        self.name = ""

        self._app = None
        self._webview = None
        self._html = None
        self._base_url = None
        self._presented = False

        self._static_directory = None
        self._static_server = None
        self._static_server_thread = None

    def resolve_base_url(self, directory):
        directory = Path(directory).expanduser().resolve()

        if not directory.is_dir():
            raise NotADirectoryError(directory)

        if (
            self._static_server is not None
            and self._static_directory == directory
            and self._static_server_thread.is_alive()
        ):
            return self._base_url

        self._stop_static_server()

        handler = partial(
            _StaticRequestHandler,
            directory=str(directory),
        )
        server = ThreadingHTTPServer(
            (_LOOPBACK_HOST, 0),
            handler,
        )
        thread = Thread(
            target=server.serve_forever,
            name="webspan-static-server",
            daemon=True,
        )

        try:
            thread.start()
        except Exception:
            server.server_close()
            raise

        port = server.server_address[1]
        self._static_directory = directory
        self._static_server = server
        self._static_server_thread = thread
        self._base_url = f"http://{_LOOPBACK_HOST}:{port}/"

        return self._base_url

    def load_html(self, html):
        self._html = html

        if self._webview is not None:
            self._webview.set_content(
                self._base_url or "",
                html,
            )

    def eval_js(self, javascript):
        if self._webview is None:
            raise RuntimeError("WebView has not been presented")

        self._webview.evaluate_javascript(javascript)

    def present(self, style=None):
        if self._presented:
            return

        self._presented = True
        self._app = toga.App(
            formal_name=self.name or "WebSpan Debug",
            app_id="dev.webspan.debug",
            startup=self._startup,
        )

    def wait_modal(self):
        if self._app is None:
            raise RuntimeError("Call present() before wait_modal()")

        try:
            self._app.main_loop()
        finally:
            self.release_base_url()

    def close(self):
        self.release_base_url()

    def release_base_url(self):
        self._stop_static_server()

    def schedule_ui(self, callback, delay=0):
        if self._app is None:
            raise RuntimeError("WebView has not been presented")

        if delay:
            self._app.loop.call_soon_threadsafe(
                self._app.loop.call_later,
                delay,
                callback,
            )
            return

        self._app.loop.call_soon_threadsafe(callback)

    def _startup(self, app):
        app.main_window.size = _IPHONE_PORTRAIT_SIZE

        self._webview = toga.WebView(
            on_navigation_starting=self._on_navigation_starting,
        )

        if self._html is not None:
            self._webview.set_content(
                self._base_url or "",
                self._html,
            )

        return self._webview

    def _on_navigation_starting(self, widget, url, **kwargs):
        if self.delegate is None:
            return True

        return self.delegate.webview_should_start_load(
            self,
            url,
            None,
        )

    def _stop_static_server(self):
        server = self._static_server
        thread = self._static_server_thread

        self._static_directory = None
        self._static_server = None
        self._static_server_thread = None
        self._base_url = None

        if server is None:
            return

        try:
            if (
                thread is not None
                and thread.is_alive()
                and thread is not current_thread()
            ):
                server.shutdown()
        finally:
            server.server_close()

            if (
                thread is not None
                and thread.is_alive()
                and thread is not current_thread()
            ):
                thread.join()


class _UI:
    WebView = WebView


ui = _UI()
