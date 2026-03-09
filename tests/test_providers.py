"""Regression tests: Kivy text and window providers must load without CRITICAL errors."""
import pytest


def test_text_provider_pil():
    """Pillow must satisfy Kivy's text provider requirement."""
    import importlib
    pil = importlib.util.find_spec("PIL")
    assert pil is not None, "PIL (Pillow) not installed — Kivy text provider will fail"


def test_window_provider_pygame():
    """pygame must be installed as Kivy window provider fallback on Python 3.14+."""
    import importlib
    pg = importlib.util.find_spec("pygame")
    assert pg is not None, "pygame not installed — Kivy window provider will fail (SDL2 binary absent for Python 3.14)"


def test_kivy_window_loads():
    """Kivy Window must load without raising an exception."""
    import os
    os.environ.setdefault("KIVY_NO_ENV_CONFIG", "1")
    # headless to avoid display requirement in CI
    os.environ["KIVY_WINDOW"] = "headless"
    try:
        from kivy.core.window import Window  # noqa: F401
    except Exception as e:
        pytest.fail(f"Kivy Window provider failed to load: {e}")
