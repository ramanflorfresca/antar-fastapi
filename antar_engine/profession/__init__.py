"""
antar_engine/profession — "what career suits me" standing-chart engine.

ISOLATED + GATED. Reads D10 (Dasamsa) + Amatyakaraka-house + Karakamsa, converges
them into ONE vocational archetype + 3-4 modern arenas, behind a conviction gate.
NOT KP. No horary, no number. Surfaces nothing until the gate passes + Raman's go.
"""

from .profession_service import get_profession_read
from .profession_gate import is_gate_open

__all__ = ["get_profession_read", "is_gate_open"]
