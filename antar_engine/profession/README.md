# antar_engine/profession — "what career suits me"

A **standing-chart** vocational engine. **NOT KP.** No horary, no number, no
moment-of-question. It reads the birth chart's divisional + Jaimini career
signal and converges it into **one vocational archetype + 3–4 modern arenas**.

> **Doctrine:** Python computes the deterministic signature; the surface is
> jargon-free (project rule 12 — no planet names, house numbers, sign names, or
> Sanskrit reach the frontend). The engine stays **quarantined behind its
> conviction gate** until it validates against known charts **and Raman approves**.
> Nothing is wired into any endpoint.

## Primary signature — three sources that must CONVERGE
1. **D10 (Dasamsa)** — *what the work IS*: D10 lagna lord, planets in/aspecting
   the D10 10th, the strongest D10 planet.
2. **Amatyakaraka + its D1 house** — *the heart of it*:
   - AmK → 10th = mainstream career / status
   - AmK → 5th  = creative / speculative / education / performance
   - AmK → 8th  = research / transformation / other-people's-money / occult / crisis
   - AmK → 3rd  = communication / media / self-effort / entrepreneurship
   - AmK → 7th  = business / partnership / public-facing
3. **Karakamsa + 10th-from-Karakamsa** — *the soul's vocation*.

## Strength gate
A signature becomes a *recommendation* only if its driving planet is dignified
(exalted or own) in **D1 OR D10 OR D9** — **D10 counts double** (it is the
career chart). Conviction points: D1 = 1, D9 = 1, D10 = 2 →
`strong` (≥3) / `supported` (≥1) / `exploratory` (0).

## Output
- **archetype** — one vocational archetype, reusing
  `natal_signatures.ARCHETYPE_LIBRARY` (THE CATALYST / THE ARCHITECT / THE
  HEALER / THE REBEL …), pointed at career via the dominant planet.
- **arenas** — 3–4 modern arenas that are **four faces of one signature** (all
  drawn from the dominant planet, lensed by the AmK house family), each tagged
  to its driving source (D10 / AmK-house / Karakamsa) in the evidence block.

## Modules
- `profession_signature.py` — D10 + AmK-house + Karakamsa convergence, dignity /
  strength gate, career-weight aggregation. Pure longitude math (no ephemeris).
- `profession_archetype.py` — dominant planet → archetype + ranked modern arenas.
- `profession_service.py` — orchestrator; `get_profession_read()`; jargon-free
  surface vs internal evidence; consults the gate.
- `profession_gate.py` — **THE GATE.** Validates archetype/arena vs known
  charts+professions; refuses to open on placeholder/example rows; `is_gate_open()`
  is the single source of truth any future surface MUST consult.

## Run (sandbox-safe — no Swiss Ephemeris)
```
python -m antar_engine.profession.selftest          # smoke test on a synthetic chart
python -m antar_engine.profession.profession_gate   # gate status (RED until validated)
```

## To pass the gate (what's needed from Raman)
Copy `validation/profession_validation.template.json` →
`validation/profession_validation.json` and fill **≥ 8 real charts** whose
profession you actually know, with `expected_arena_keywords` (and optional
`expected_archetype`). Then `profession_gate` scores accuracy and writes
`validation/profession_gate_status.json`. Integration into a surface happens
**only** after the gate passes and you give the go.
```
