"""
selftest.py — smoke test for A1-A3. RUN ON THE MAC VENV:

    cd ~/antarai && source venv311/bin/activate
    python -m antar_engine.kp.selftest

Checks: 249-sub table integrity, a full natal KP chart, the verdict engine on a
few question types, and a horary answer with a timed window. Read-only.
"""

from datetime import datetime

from .kp_chart import compute_kp_chart, _SUB_SEGMENTS, resolve_sublord
from .kp_significators import verdict
from .kp_horary import answer_horary


def main():
    # 1) table integrity (no ephemeris)
    assert len(_SUB_SEGMENTS) == 249, len(_SUB_SEGMENTS)
    span = sum(s["end"] - s["start"] for s in _SUB_SEGMENTS)
    assert abs(span - 360.0) < 1e-6, span
    print(f"[OK] sub table: {len(_SUB_SEGMENTS)} segments, span {span:.4f}")
    t = resolve_sublord(0.0)
    print(f"[OK] 0deg Aries -> {t['nakshatra']} star={t['star_lord']} "
          f"sub={t['sub_lord']}")

    # 2) natal chart
    chart = compute_kp_chart("1974-11-26", "11:59", 28.6139, 77.2090,
                             tz_offset=5.5)
    print(f"[OK] natal ASC {chart['ascendant']['sign']} "
          f"sub={chart['ascendant']['sub_lord']} ayan={chart['ayanamsa_value']}")

    # 3) verdicts
    for q in ("gain", "job_new", "marriage", "promotion"):
        r = verdict(chart, q)
        print(f"     verdict {q:>10}: {r['verdict']:<11} conf={r['confidence']} "
              f"CSL={r['debug']['cuspal_sub_lord']}")
    rl = verdict(chart, "loss", loss_house=7)
    print(f"     verdict {'loss(7)':>10}: {rl['verdict']} conf={rl['confidence']}")

    # 4) horary
    res = answer_horary(74, "gain", datetime(2026, 6, 23, 14, 30),
                        28.6139, 77.2090, tz_offset=5.5)
    print(f"[OK] horary #74 gain: {res['verdict']} conf={res['confidence']} "
          f"window={res['window']['start']}..{res['window']['end']} "
          f"({res['window']['basis']})")
    print(f"     RP set: {res['ruling_planets']['set']}")
    print("\nALL SMOKE CHECKS RAN.")


if __name__ == "__main__":
    main()
