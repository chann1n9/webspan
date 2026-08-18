import warnings


class WebSpanCore:
    def __init__(self):
        self._handlers = {}

    def route(self, name):
        """Deprecated: register handlers explicitly with register()."""
        warnings.warn(
            "route() is deprecated; use register() instead",
            DeprecationWarning,
            stacklevel=2,
        )

        def decorator(func):
            self.register(name, func)
            return func

        return decorator

    def register(self, name, func):
        if name in self._handlers:
            raise ValueError(f"Route already registered: {name}")

        self._handlers[name] = func

    def dispatch(self, method, data):
        handler = self._handlers.get(method)

        if handler is None:
            raise LookupError(f"Unknown webspan method: {method}")

        return handler(data)
