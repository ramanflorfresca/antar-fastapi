"""
antar_engine.kp — Krishnamurti Paddhati (KP) sub-system.

ISOLATED, PARALLEL house system. Does NOT modify the Lahiri / whole-sign base
chart used everywhere else in Antar. KP runs a SECOND chart computation:
Placidus cusps + KP (Krishnamurti) ayanamsa, with the 249-sub division.

Powers (post-gate only): the ASK surface (binary / timed questions) and
intraday windows. Quarantined behind kp_backtest until the binary-outcome
validation gate passes AND Raman approves. No KP output reaches a user before
then.

Doctrine: Python computes the entire deterministic sub-lord chain; Claude only
narrates the structured verdict bundle. Zero KP jargon on any user surface.
"""

KP_VERSION = "0.1.0-foundation"
