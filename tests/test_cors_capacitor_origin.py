"""The bundled iOS app calls the API from capacitor://localhost."""
import re
from pathlib import Path


def _regex():
    src = (Path(__file__).resolve().parent.parent / "main.py").read_text()
    start = src.index("_ANTAR_CORS_ORIGIN_REGEX = (")
    end = src.index("\n)\n", start)
    ns = {}
    exec(src[start:end + 2], ns)
    return re.compile(ns["_ANTAR_CORS_ORIGIN_REGEX"])


def test_allows_native_and_web_origins():
    rx = _regex()
    for o in ("capacitor://localhost", "https://localhost", "https://antar.world",
              "https://www.antar.world", "http://localhost:5173".replace("http", "https")):
        assert rx.match(o), o


def test_rejects_lookalikes():
    rx = _regex()
    for o in ("capacitor://evil.com", "capacitor://localhost.evil.com",
              "http://antar.world", "https://antar.world.evil.com", "https://evilantar.world"):
        assert not rx.match(o), o
