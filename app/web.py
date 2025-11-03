from gunicorn.app.base import BaseApplication
from gunicorn.util import import_app


class GunicornApplication(BaseApplication):
    """Custom Gunicorn application for running FastAPI with uvicorn workers."""

    def __init__(self, app_uri: str, options: dict | None = None):
        self.app_uri = app_uri
        self.options = options or {}
        super().__init__()

    def load_config(self):
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key.lower(), value)

    def load(self):
        return import_app(self.app_uri)
