#!/usr/bin/env python3
"""
scripts/generate_mantra_audio.py
─────────────────────────────────────────────────────────────────────────────
One-time ElevenLabs generation of the 48 mantra audio files:
    9 planets  x 3 languages (en/es/pt)  = 27
    7 chakras  x 3 languages              = 21
Each file = ONE slow, clear repetition (frontend loops it). MP3, 128 kbps.

Run once, cache forever in the public Supabase bucket `practice-audio`.

Usage:
    # 1. Pick a voice — generate the same mantra in the 3 candidate voices:
    python scripts/generate_mantra_audio.py --sample

    # 2. Lock VOICE_ID below (or pass --voice), then generate everything:
    python scripts/generate_mantra_audio.py --all

    # Targeted:
    python scripts/generate_mantra_audio.py --planet Saturn --lang en
    python scripts/generate_mantra_audio.py --chakra throat --lang es

    # Generate AND upload to Supabase storage in one go:
    python scripts/generate_mantra_audio.py --all --upload

Env:
    ELEVENLABS_API_KEY   (required; falls back to ELEVEN_LABS_API_KEY)
    SUPABASE_URL, SUPABASE_SERVICE_KEY  (required only for --upload)
"""

import argparse
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load the project .env so SUPABASE_* / ELEVENLABS_API_KEY work without exporting.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
                override=False)
except Exception:
    pass

from antar_engine.practice_library import PRACTICE_LIBRARY
from antar_engine.practice_chakras import CHAKRA_MANTRAS

ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVEN_LABS_API_KEY")


def _supabase_service_key():
    """Service-role key (can create buckets + write storage). Anon key cannot."""
    return (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or os.environ.get("SUPABASE_SERVICE_KEY")
            or os.environ.get("SUPABASE_KEY"))

# Candidate voices to audition (see --sample). Lock ONE for all 48 files.
CANDIDATE_VOICES = {
    "Adam":   "rOFKO5wKBhxNl5XSeENO",   # male, calm, deep
    "Antoni": "ErXwobaYiN019PkySvjV",   # male, soft, even pace
    "Bella":  "EXAVITQu4vr4xnSDxMaL",   # female, warm
}
VOICE_ID = "ErXwobaYiN019PkySvjV"       # default = Antoni; override with --voice

VOICE_SETTINGS = {
    "stability": 0.75,
    "similarity_boost": 0.75,
    "style": 0.0,
    "use_speaker_boost": True,
}

MODEL_ID = "eleven_multilingual_v2"
OUTPUT_FORMAT = "mp3_44100_128"          # MP3, 128 kbps
LANGUAGES = ["en", "es", "pt"]
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "audio")
BUCKET = "practice-audio"


def list_voices():
    """Print the voice IDs actually available on this account."""
    if not ELEVEN_API_KEY:
        sys.exit("ERROR: ELEVENLABS_API_KEY not set")
    r = requests.get("https://api.elevenlabs.io/v1/voices",
                     headers={"xi-api-key": ELEVEN_API_KEY}, timeout=30)
    if r.status_code != 200:
        sys.exit(f"ERROR listing voices: {r.status_code} {r.text}")
    voices = r.json().get("voices", [])
    print(f"{len(voices)} voices available:\n")
    for v in voices:
        print(f"  {v.get('voice_id')}  {v.get('name'):<20} [{v.get('category')}]")
    print("\nPick one, then: --voice <voice_id> --all")


def _tts(text: str, voice_id: str) -> bytes:
    if not ELEVEN_API_KEY:
        sys.exit("ERROR: ELEVENLABS_API_KEY not set")
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"},
        params={"output_format": OUTPUT_FORMAT},
        json={"text": text, "voice_settings": VOICE_SETTINGS, "model_id": MODEL_ID},
        timeout=60,
    )
    if r.status_code != 200:
        # Surface the real API message (e.g. voice_id not in your library).
        msg = r.text
        if r.status_code == 404:
            msg += ("\n\nThat voice_id is not on your account. "
                    "Run:  python scripts/generate_mantra_audio.py --list-voices  "
                    "and pass one of those IDs with --voice.")
        sys.exit(f"ERROR {r.status_code} from ElevenLabs:\n{msg}")
    return r.content


def _write(name: str, content: bytes) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    with open(path, "wb") as f:
        f.write(content)
    print(f"GENERATED {name} ({len(content)} bytes)")
    return path


def _mantra_text(sanskrit: str, translit: str, use_translit: bool) -> str:
    # Sanskrit script renders on the multilingual voices; fall back to
    # transliteration if a voice anglicises it.
    return translit if use_translit else (sanskrit or translit)


def _targets(args):
    """Yield (filename_stem, text) pairs to generate."""
    use_translit = args.translit
    langs = [args.lang] if args.lang else LANGUAGES

    planets = [args.planet] if args.planet else (list(PRACTICE_LIBRARY) if not args.chakra else [])
    for planet in planets:
        m = PRACTICE_LIBRARY[planet]["mantra"]
        text = _mantra_text(m["sanskrit"], m["translit"], use_translit)
        for lang in langs:
            yield f"{planet.lower()}-{lang}.mp3", text

    chakras = [args.chakra] if args.chakra else (list(CHAKRA_MANTRAS) if not args.planet else [])
    for ck in chakras:
        m = CHAKRA_MANTRAS[ck]
        text = _mantra_text(m["sanskrit"], m["translit"], use_translit)
        for lang in langs:
            yield f"chakra-{ck}-{lang}.mp3", text


def _ensure_bucket(url, key):
    """Create the public practice-audio bucket if it doesn't exist (REST, version-proof)."""
    hdr = {"Authorization": f"Bearer {key}", "apikey": key, "Content-Type": "application/json"}
    # Already there?
    g = requests.get(f"{url.rstrip('/')}/storage/v1/bucket/{BUCKET}", headers=hdr, timeout=30)
    if g.status_code == 200:
        print(f"bucket '{BUCKET}' already exists")
        return
    # Minimal payload — most compatible across Supabase versions.
    r = requests.post(
        f"{url.rstrip('/')}/storage/v1/bucket", headers=hdr,
        json={"id": BUCKET, "name": BUCKET, "public": True}, timeout=30,
    )
    if r.status_code in (200, 201):
        print(f"CREATED public bucket '{BUCKET}'")
    elif r.status_code == 409 or "already exists" in r.text.lower() or "duplicate" in r.text.lower():
        print(f"bucket '{BUCKET}' already exists")
    else:
        sys.exit(f"ERROR creating bucket (status {r.status_code}): {r.text}\n"
                 "If this is a 403/401, SUPABASE_SERVICE_ROLE_KEY is wrong (anon keys cannot create buckets).\n"
                 "Or create it once in the dashboard: Storage -> New bucket -> 'practice-audio' -> Public.")


def _upload(paths):
    url = os.environ.get("SUPABASE_URL")
    key = _supabase_service_key()
    if not (url and key):
        sys.exit("ERROR: --upload needs SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY")
    _ensure_bucket(url, key)
    try:
        from supabase import create_client
    except Exception:
        sys.exit("ERROR: pip install supabase  (for --upload)")
    sb = create_client(url, key)
    for p in paths:
        name = os.path.basename(p)
        with open(p, "rb") as f:
            data = f.read()
        try:
            sb.storage.from_(BUCKET).upload(
                name, data,
                {"content-type": "audio/mpeg", "upsert": "true", "cache-control": "31536000"},
            )
            print(f"UPLOADED {BUCKET}/{name}")
        except Exception as e:
            print(f"UPLOAD FAILED {name}: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--planet", help="single planet, e.g. Saturn")
    ap.add_argument("--chakra", help="single chakra key, e.g. throat")
    ap.add_argument("--lang", choices=LANGUAGES, help="single language")
    ap.add_argument("--all", action="store_true", help="all 48 files")
    ap.add_argument("--translit", action="store_true", help="use transliteration text instead of Sanskrit script")
    ap.add_argument("--voice", help="override VOICE_ID")
    ap.add_argument("--sample", action="store_true", help="audition candidate voices on one mantra")
    ap.add_argument("--list-voices", action="store_true", help="list voice IDs available on your account")
    ap.add_argument("--upload", action="store_true", help="upload generated files to Supabase storage")
    ap.add_argument("--force", action="store_true", help="regenerate even if the file exists")
    args = ap.parse_args()

    if args.list_voices:
        list_voices()
        return

    if args.sample:
        text = PRACTICE_LIBRARY["Saturn"]["mantra"]["sanskrit"]
        # If --voice given, audition just that one; else try the candidates and
        # skip any that aren't on this account (404).
        candidates = {"chosen": args.voice} if args.voice else CANDIDATE_VOICES
        ok = 0
        for vname, vid in candidates.items():
            try:
                _write(f"_sample-{vname.lower()}.mp3", _tts(text, vid))
                ok += 1
            except SystemExit as e:
                print(f"  skip {vname} ({vid}): {str(e).splitlines()[0]}")
        if ok == 0:
            print("\nNone of the candidate IDs are on your account. Run:\n"
                  "  python scripts/generate_mantra_audio.py --list-voices\n"
                  "then audition one with:  --sample --voice <voice_id>")
        else:
            print(f"\n{ok} sample(s) written. Listen, then run --all --voice <id>.")
        return

    voice = args.voice or VOICE_ID
    if not (args.all or args.planet or args.chakra):
        ap.error("pass --all, or --planet/--chakra (optionally with --lang), or --sample")

    written = []
    for name, text in _targets(args):
        path = os.path.join(OUT_DIR, name)
        if os.path.exists(path) and not args.force:
            print(f"SKIP {name} (exists)")
            written.append(path)
            continue
        written.append(_write(name, _tts(text, voice)))

    print(f"\n{len(written)} file(s) ready in {OUT_DIR}")
    if args.upload:
        _upload(written)


if __name__ == "__main__":
    main()
