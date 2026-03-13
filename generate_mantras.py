"""
Antar.world — Mantra Audio Generator using ElevenLabs
Generates all mantra audio files and uploads to Supabase storage.

Install:
    pip install elevenlabs supabase python-dotenv

Setup .env:
    ELEVENLABS_API_KEY=sk_84423e71e9cf93e9c3c65ba8808e9701bdf42c0bade29396
    SUPABASE_URL=https://ovszdbymflpwnynmpgqk.supabase.co
    SUPABASE_KEY=sk-b46e5c71f198471cae0f7bf77adceb10
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from supabase import create_client

load_dotenv()

client    = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
supabase  = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
BUCKET    = "antar-mantras"
OUT_DIR   = Path("./generated_mantras")
OUT_DIR.mkdir(exist_ok=True)

# ─── VOICE SETTINGS ──────────────────────────────────────────────────────────
# Use a deep, calm, meditative male voice
# Best ElevenLabs voices for mantras:
#   "Daniel"     - Deep, authoritative
#   "Antoni"     - Warm, meditative  
#   "Arnold"     - Deep resonant
#   "Patrick"    - Slow, deliberate
# Or clone a voice from a real pandit recording for best results

VOICE_ID = "t0jbNlBVZ17f02VDIeMI"  # Arjun — deep and resonant
# Alternative: "ErXwobaYiN019PkySvjV"  # Antoni — warm

VOICE_SETTINGS = VoiceSettings(
    stability=0.85,          # High stability = consistent, less variation (good for mantras)
    similarity_boost=0.75,
    style=0.15,              # Low style = neutral, meditative
    use_speaker_boost=True,
)

# ─── ALL MANTRAS TO GENERATE ─────────────────────────────────────────────────

MANTRAS = {

    # ── PLANET BEEJ MANTRAS ──────────────────────────────────────────────────
    "planets/sun_beej_mantra": {
        "text": "Om Hraam... Hreem... Hraum... Sah... Suryaya Namah. Om Hraam... Hreem... Hraum... Sah... Suryaya Namah. Om Hraam... Hreem... Hraum... Sah... Suryaya Namah.",
        "description": "Sun Beej Mantra — chant at sunrise on Sundays, 7 times"
    },
    "planets/moon_beej_mantra": {
        "text": "Om Shraam... Shreem... Shraum... Sah... Chandraya Namah. Om Shraam... Shreem... Shraum... Sah... Chandraya Namah. Om Shraam... Shreem... Shraum... Sah... Chandraya Namah.",
        "description": "Moon Beej Mantra — chant on Monday evenings, 11 times"
    },
    "planets/mars_beej_mantra": {
        "text": "Om Kraam... Kreem... Kraum... Sah... Bhaumaya Namah. Om Kraam... Kreem... Kraum... Sah... Bhaumaya Namah. Om Kraam... Kreem... Kraum... Sah... Bhaumaya Namah.",
        "description": "Mars Beej Mantra — chant on Tuesday mornings, 21 times"
    },
    "planets/mercury_beej_mantra": {
        "text": "Om Braam... Breem... Braum... Sah... Budhaya Namah. Om Braam... Breem... Braum... Sah... Budhaya Namah. Om Braam... Breem... Braum... Sah... Budhaya Namah.",
        "description": "Mercury Beej Mantra — chant on Wednesday mornings, 17 times"
    },
    "planets/jupiter_beej_mantra": {
        "text": "Om Graam... Greem... Graum... Sah... Gurave Namah. Om Graam... Greem... Graum... Sah... Gurave Namah. Om Graam... Greem... Graum... Sah... Gurave Namah.",
        "description": "Jupiter Beej Mantra — chant on Thursday before sunrise, 19 times"
    },
    "planets/venus_beej_mantra": {
        "text": "Om Draam... Dreem... Draum... Sah... Shukraya Namah. Om Draam... Dreem... Draum... Sah... Shukraya Namah. Om Draam... Dreem... Draum... Sah... Shukraya Namah.",
        "description": "Venus Beej Mantra — chant on Friday mornings, 16 times"
    },
    "planets/saturn_beej_mantra": {
        "text": "Om Praam... Preem... Praum... Sah... Shanaischaraya Namah. Om Praam... Preem... Praum... Sah... Shanaischaraya Namah. Om Praam... Preem... Praum... Sah... Shanaischaraya Namah.",
        "description": "Saturn Beej Mantra — chant on Saturday evenings at sunset, 23 times"
    },
    "planets/rahu_beej_mantra": {
        "text": "Om Bhram... Bhreem... Bhraum... Sah... Rahave Namah. Om Bhram... Bhreem... Bhraum... Sah... Rahave Namah. Om Bhram... Bhreem... Bhraum... Sah... Rahave Namah.",
        "description": "Rahu Beej Mantra — chant on Saturdays after sunset, 18 times"
    },
    "planets/ketu_beej_mantra": {
        "text": "Om Sraam... Sreem... Sraum... Sah... Ketave Namah. Om Sraam... Sreem... Sraum... Sah... Ketave Namah. Om Sraam... Sreem... Sraum... Sah... Ketave Namah.",
        "description": "Ketu Beej Mantra — chant on Tuesday evenings, 18 times"
    },

    # ── CHAKRA BIJA MANTRAS ──────────────────────────────────────────────────
    "chakras/muladhara_lam": {
        "text": "Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam... Lam.",
        "description": "Root Chakra — LAM bija mantra, 108 repetitions"
    },
    "chakras/svadhisthana_vam": {
        "text": "Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam... Vam.",
        "description": "Sacral Chakra — VAM bija mantra, 108 repetitions"
    },
    "chakras/manipura_ram": {
        "text": "Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram... Ram.",
        "description": "Solar Plexus Chakra — RAM bija mantra, 108 repetitions"
    },
    "chakras/anahata_yam": {
        "text": "Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam... Yam.",
        "description": "Heart Chakra — YAM bija mantra, 108 repetitions"
    },
    "chakras/vishuddha_ham": {
        "text": "Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham... Ham.",
        "description": "Throat Chakra — HAM bija mantra, 108 repetitions"
    },
    "chakras/ajna_om": {
        "text": "Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum... Aum.",
        "description": "Third Eye Chakra — OM bija mantra, 108 repetitions"
    },
    "chakras/sahasrara_om": {
        "text": "Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ... Aum... ... ...",
        "description": "Crown Chakra — OM into silence, slow and spacious"
    },

    # ── KEY STOTRAS ──────────────────────────────────────────────────────────
    "stotras/gayatri_mantra": {
        "text": "Om Bhur Bhuva Swaha... Tat Savitur Varenyam... Bhargo Devasya Dheemahi... Dhiyo Yo Nah Prachodayat. Om Bhur Bhuva Swaha... Tat Savitur Varenyam... Bhargo Devasya Dheemahi... Dhiyo Yo Nah Prachodayat. Om Bhur Bhuva Swaha... Tat Savitur Varenyam... Bhargo Devasya Dheemahi... Dhiyo Yo Nah Prachodayat.",
        "description": "Gayatri Mantra — the universal mantra of light and wisdom"
    },
    "stotras/mahamrityunjaya": {
        "text": "Om Tryambakam Yajamahe... Sugandhim Pushti Vardhanam... Urvarukamiva Bandhanan... Mrityor Mukshiya Maamritat. Om Tryambakam Yajamahe... Sugandhim Pushti Vardhanam... Urvarukamiva Bandhanan... Mrityor Mukshiya Maamritat. Om Tryambakam Yajamahe... Sugandhim Pushti Vardhanam... Urvarukamiva Bandhanan... Mrityor Mukshiya Maamritat.",
        "description": "Mahamrityunjaya — the great healing mantra of Shiva"
    },
    "stotras/om_namah_shivaya": {
        "text": "Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya... Om Namah Shivaya.",
        "description": "Om Namah Shivaya — Moon and Saturn healing, 27 repetitions"
    },
    "stotras/om_namo_narayanaya": {
        "text": "Om Namo Narayanaya... Om Namo Narayanaya... Om Namo Narayanaya... Om Namo Narayanaya... Om Namo Narayanaya... Om Namo Narayanaya... Om Namo Narayanaya... Om Namo Narayanaya... Om Namo Narayanaya... Om Namo Narayanaya... Om Namo Narayanaya... Om Namo Narayanaya... Om Namo Narayanaya... Om Namo Narayanaya... Om Namo Narayanaya... Om Namo Narayanaya.",
        "description": "Om Namo Narayanaya — Jupiter and Mercury remedy, Vishnu mantra"
    },
    "stotras/om_gam_ganapataye": {
        "text": "Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah... Om Gam Ganapataye Namah.",
        "description": "Ganesha mantra — Ketu remedy, removes obstacles, new beginnings"
    },
    "stotras/sri_ram_jai_ram": {
        "text": "Sri Ram... Jai Ram... Jai Jai Ram... Sri Ram... Jai Ram... Jai Jai Ram... Sri Ram... Jai Ram... Jai Jai Ram... Sri Ram... Jai Ram... Jai Jai Ram... Sri Ram... Jai Ram... Jai Jai Ram... Sri Ram... Jai Ram... Jai Jai Ram... Sri Ram... Jai Ram... Jai Jai Ram... Sri Ram... Jai Ram... Jai Jai Ram... Sri Ram... Jai Ram... Jai Jai Ram... Sri Ram... Jai Ram... Jai Jai Ram.",
        "description": "Sri Ram Jai Ram — Sun remedy, protection, victory"
    },
    "stotras/om_aim_hreem_kleem": {
        "text": "Om Aim Hreem Kleem Chamundaye Viche... Om Aim Hreem Kleem Chamundaye Viche... Om Aim Hreem Kleem Chamundaye Viche... Om Aim Hreem Kleem Chamundaye Viche... Om Aim Hreem Kleem Chamundaye Viche... Om Aim Hreem Kleem Chamundaye Viche... Om Aim Hreem Kleem Chamundaye Viche... Om Aim Hreem Kleem Chamundaye Viche... Om Aim Hreem Kleem Chamundaye Viche.",
        "description": "Durga mantra — Rahu remedy, protection from illusion and deception"
    },

    # ── SPECIAL ──────────────────────────────────────────────────────────────
    "special/om_chanting": {
        "text": "Aum............... Aum............... Aum............... Aum............... Aum............... Aum............... Aum............... Aum............... Aum............... Aum............... Aum............... Aum...............",
        "description": "Pure OM chanting — universal, all purposes, meditation anchor"
    },
    "special/navagraha_mantra": {
        "text": "Om Suryaya Namah... Om Chandraya Namah... Om Mangalaya Namah... Om Budhaya Namah... Om Brihaspataye Namah... Om Shukraya Namah... Om Shanaye Namah... Om Rahave Namah... Om Ketave Namah... Om Navagraha Devataabhyam Namah.",
        "description": "Navagraha mantra — all 9 planets, balances entire chart"
    },
}


# ─── GENERATION FUNCTION ─────────────────────────────────────────────────────

def generate_mantra(key: str, mantra: dict, model: str = "eleven_multilingual_v2") -> Path:
    """Generate a single mantra audio file using ElevenLabs."""
    
    folder = OUT_DIR / key.split("/")[0]
    folder.mkdir(exist_ok=True)
    filename = key.split("/")[1] + ".mp3"
    filepath = folder / filename
    
    if filepath.exists():
        print(f"  ⏭  Skipping {key} (already exists)")
        return filepath
    
    print(f"  🎙  Generating: {key}")
    print(f"      {mantra['description']}")
    
    audio = client.text_to_speech.convert(
        voice_id=VOICE_ID,
        text=mantra["text"],
        model_id=model,
        voice_settings=VOICE_SETTINGS,
        output_format="mp3_44100_128",  # High quality for spiritual audio
    )
    
    with open(filepath, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    
    print(f"      ✓ Saved: {filepath} ({filepath.stat().st_size // 1024}KB)")
    return filepath


def upload_to_supabase(filepath: Path, bucket_path: str):
    """Upload a generated audio file to Supabase storage."""
    
    with open(filepath, "rb") as f:
        data = f.read()
    
    res = supabase.storage.from_(BUCKET).upload(
        path=bucket_path,
        file=data,
        file_options={"content-type": "audio/mpeg", "upsert": "true"},
    )
    print(f"      ☁  Uploaded to Supabase: {bucket_path}")
    return res


def generate_all(upload: bool = False, category: str = None):
    """
    Generate all mantras and optionally upload to Supabase.
    
    Args:
        upload: If True, upload each file to Supabase after generation
        category: If set, only generate this category (e.g. 'planets', 'chakras', 'stotras')
    """
    
    print("\n🕉  Antar.world — Mantra Audio Generator")
    print("=" * 50)
    
    items = MANTRAS.items()
    if category:
        items = [(k, v) for k, v in items if k.startswith(category)]
    
    generated = []
    failed    = []
    
    for key, mantra in items:
        try:
            filepath = generate_mantra(key, mantra)
            generated.append(filepath)
            
            if upload:
                bucket_path = key + ".mp3"
                upload_to_supabase(filepath, bucket_path)
            
            # Rate limit — ElevenLabs allows ~2 requests/sec on starter plan
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ✗  Failed: {key} — {e}")
            failed.append(key)
    
    print("\n" + "=" * 50)
    print(f"✓ Generated: {len(generated)} files")
    print(f"✗ Failed:    {len(failed)} files")
    if failed:
        print(f"  Failed keys: {failed}")
    print(f"📁 Output directory: {OUT_DIR.absolute()}")
    
    if upload:
        print(f"☁  All files uploaded to Supabase bucket: {BUCKET}")


# ─── ESTIMATED COST ──────────────────────────────────────────────────────────

def estimate_cost():
    """Estimate ElevenLabs character cost for all mantras."""
    total_chars = sum(len(m["text"]) for m in MANTRAS.values())
    
    # ElevenLabs pricing (as of 2025):
    # Starter: $5/month = 30,000 chars
    # Creator: $22/month = 100,000 chars  
    # Pro:     $99/month = 500,000 chars
    
    print(f"\n📊 Cost Estimate:")
    print(f"   Total mantras: {len(MANTRAS)}")
    print(f"   Total characters: {total_chars:,}")
    print(f"   Starter plan (30K chars/month): {'1 month' if total_chars <= 30000 else f'{total_chars/30000:.1f} months'}")
    print(f"   Creator plan (100K chars/month): {'fits in 1 month' if total_chars <= 100000 else f'{total_chars/100000:.1f} months'}")
    print(f"\n   Estimated cost: ${max(5, (total_chars/30000)*5):.0f} total (one-time generation)")
    print(f"   These are permanent files — generate once, serve forever from Supabase.")


# ─── SUPABASE BUCKET SETUP SQL ───────────────────────────────────────────────

SUPABASE_SQL = """
-- Run this in your Supabase SQL editor BEFORE uploading

-- 1. Create the bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'antar-mantras',
    'antar-mantras', 
    true,
    10485760,  -- 10MB per file limit
    ARRAY['audio/mpeg', 'audio/mp3', 'audio/wav']
)
ON CONFLICT (id) DO NOTHING;

-- 2. Public read policy (anyone can play mantras)
CREATE POLICY "Public read - mantras"
ON storage.objects FOR SELECT
USING (bucket_id = 'antar-mantras');

-- 3. Authenticated upload policy (only your service role uploads)
CREATE POLICY "Service role upload - mantras"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'antar-mantras');
"""


# ─── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    if "--estimate" in sys.argv:
        estimate_cost()
    
    elif "--generate" in sys.argv:
        category = None
        for arg in sys.argv:
            if arg.startswith("--category="):
                category = arg.split("=")[1]
        
        upload = "--upload" in sys.argv
        generate_all(upload=upload, category=category)
    
    elif "--sql" in sys.argv:
        print(SUPABASE_SQL)
    
    else:
        print("""
🕉  Antar.world Mantra Generator

Usage:
  python generate_mantras.py --estimate              # Show cost estimate
  python generate_mantras.py --generate              # Generate all locally
  python generate_mantras.py --generate --upload     # Generate + upload to Supabase
  python generate_mantras.py --generate --category=planets   # Only planets
  python generate_mantras.py --generate --category=chakras   # Only chakras
  python generate_mantras.py --generate --category=stotras   # Only stotras
  python generate_mantras.py --sql                   # Print Supabase setup SQL

Categories: planets, chakras, stotras, special
        """)
