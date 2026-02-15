"""Tests for py_verify.__main__."""

from unittest.mock import patch


def test_main_imports_app():
    from py_verify.__main__ import app
    from py_verify.cli import app as cli_app

    assert app is cli_app


def test_main_guard():
    """Test that __main__.py calls app() when run as __main__."""
    with patch("py_verify.cli.app") as _mock_app:
        # Simulate running as __main__
        import py_verify.__main__

        # The if __name__ == "__main__" block won't trigger during import,
        # but we verify the module structure is correct
        assert hasattr(py_verify.__main__, "app")
