from .base import *

# Test environment only. Loaded exclusively by pytest
# (see ``[tool.pytest.ini_options]`` in ``pyproject.toml``); development and
# production continue to use the secure default hashers from ``base.py``.
#
# The default PBKDF2 hasher runs hundreds of thousands of iterations per call,
# which dominates the suite runtime because most tests create users. MD5 is a
# built-in Django hasher (no extra dependency) and is only ever reached here.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Tests never render error pages; keep the flag explicit rather than inheriting
# the development default (pytest-django also forces DEBUG=False during runs).
DEBUG = False
