"""Tests for py_smart_verify.__init__."""

import py_smart_verify


def test_version_is_string():
    assert isinstance(py_smart_verify.__version__, str)


def test_version_format():
    parts = py_smart_verify.__version__.split(".")
    assert len(parts) == 3
    for part in parts:
        assert part.isdigit()


def test_app_name():
    assert py_smart_verify.__app_name__ == "py-smart-verify"
