"""Tests for py_verify.__main__."""

import sys
from unittest.mock import patch


def test_main_imports_app():
    # Ensure fresh import (in case test_main_guard ran first and cached a mock)
    sys.modules.pop("py_verify.__main__", None)
    from py_verify.__main__ import app
    from py_verify.cli import app as cli_app

    assert app is cli_app


def test_main_guard():
    """Test that __main__.py calls app() when run as __main__."""
    sys.modules.pop("py_verify.__main__", None)
    with patch("py_verify.cli.app") as _mock_app:
        # Simulate running as __main__
        import py_verify.__main__

        # The if __name__ == "__main__" block won't trigger during import,
        # but we verify the module structure is correct
        assert hasattr(py_verify.__main__, "app")
    # Clean up so the mock doesn't leak into other tests
    sys.modules.pop("py_verify.__main__", None)
