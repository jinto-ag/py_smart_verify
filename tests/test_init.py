"""Tests for py_verify.__init__."""

import py_verify


def test_version_is_string():
    assert isinstance(py_verify.__version__, str)


def test_version_format():
    parts = py_verify.__version__.split(".")
    assert len(parts) == 3
    for part in parts:
        assert part.isdigit()


def test_app_name():
    assert py_verify.__app_name__ == "py-verify"
