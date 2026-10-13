"""Opt-in integration initializes Julia before tests import the Torch adapter."""

import os

if os.getenv("RUN_PYSR_TESTS") == "1":
    import pysr  # noqa: F401
