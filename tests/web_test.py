import sys
from unittest.mock import MagicMock, patch

import pytest

# Skip all tests on Windows because gunicorn uses Unix-only modules (fcntl)
pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="Gunicorn is not supported on Windows (uses fcntl module)"
)


class TestGunicornApplication:
    """Tests for the custom GunicornApplication class."""

    def test_init_with_app_uri(self):
        """Test GunicornApplication initialization with app URI."""
        from app.web import GunicornApplication

        with patch.object(GunicornApplication, "load_config"):
            app = GunicornApplication("app.main:app")

            assert app.app_uri == "app.main:app"
            assert app.options == {}

    def test_init_with_options(self):
        """Test GunicornApplication initialization with options."""
        from app.web import GunicornApplication

        options = {
            "bind": "0.0.0.0:8000",
            "workers": 4,
            "worker_class": "uvicorn.workers.UvicornWorker",
        }

        with patch.object(GunicornApplication, "load_config"):
            app = GunicornApplication("app.main:app", options=options)

            assert app.app_uri == "app.main:app"
            assert app.options == options

    def test_load_config(self):
        """Test load_config applies options to gunicorn config."""
        from app.web import GunicornApplication

        options = {
            "bind": "127.0.0.1:8080",
            "workers": 2,
        }

        # Mock the parent class init and cfg
        with patch("gunicorn.app.base.BaseApplication.__init__", return_value=None):
            app = GunicornApplication("app.main:app", options=options)

            # Create a mock cfg object
            app.cfg = MagicMock()
            app.cfg.settings = {"bind": MagicMock(), "workers": MagicMock()}

            app.load_config()

            # Verify cfg.set was called for each option in settings
            app.cfg.set.assert_any_call("bind", "127.0.0.1:8080")
            app.cfg.set.assert_any_call("workers", 2)

    def test_load_config_ignores_unknown_settings(self):
        """Test load_config ignores settings not in gunicorn cfg."""
        from app.web import GunicornApplication

        options = {
            "bind": "127.0.0.1:8080",
            "unknown_setting": "value",  # Not a valid gunicorn setting
        }

        with patch("gunicorn.app.base.BaseApplication.__init__", return_value=None):
            app = GunicornApplication("app.main:app", options=options)

            # Create a mock cfg object without unknown_setting
            app.cfg = MagicMock()
            app.cfg.settings = {"bind": MagicMock()}

            app.load_config()

            # Only bind should be set, not unknown_setting
            app.cfg.set.assert_called_once_with("bind", "127.0.0.1:8080")

    def test_load_config_ignores_none_values(self):
        """Test load_config ignores options with None values."""
        from app.web import GunicornApplication

        options = {
            "bind": "127.0.0.1:8080",
            "workers": None,  # Should be ignored
        }

        with patch("gunicorn.app.base.BaseApplication.__init__", return_value=None):
            app = GunicornApplication("app.main:app", options=options)

            # Create a mock cfg object
            app.cfg = MagicMock()
            app.cfg.settings = {"bind": MagicMock(), "workers": MagicMock()}

            app.load_config()

            # Only bind should be set, not workers with None value
            app.cfg.set.assert_called_once_with("bind", "127.0.0.1:8080")

    def test_load(self):
        """Test load method imports and returns the application."""
        from app.web import GunicornApplication

        with patch("gunicorn.app.base.BaseApplication.__init__", return_value=None):
            with patch("gunicorn.util.import_app") as mock_import:
                mock_app = MagicMock()
                mock_import.return_value = mock_app

                app = GunicornApplication("app.main:app")
                loaded_app = app.load()

                mock_import.assert_called_once_with("app.main:app")
                assert loaded_app == mock_app

    def test_load_with_different_app_uri(self):
        """Test load method with different app URI."""
        from app.web import GunicornApplication

        with patch("gunicorn.app.base.BaseApplication.__init__", return_value=None):
            with patch("gunicorn.util.import_app") as mock_import:
                mock_app = MagicMock()
                mock_import.return_value = mock_app

                app = GunicornApplication("custom.module:application")
                loaded_app = app.load()

                mock_import.assert_called_once_with("custom.module:application")
                assert loaded_app == mock_app
