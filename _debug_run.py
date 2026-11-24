import faulthandler
import sys

# Précharger les imports lourds (fastapi, jose, bcrypt) hors du watchdog
import app.main  # noqa: F401
import pytest

# Watchdog : si la suite dépasse 90 s, dump de toutes les piles puis sortie
faulthandler.dump_traceback_later(90, exit=True)

sys.exit(
    pytest.main(
        ["-v", "-s", "-p", "no:cacheprovider", "tests/test_otp.py"]
    )
)
