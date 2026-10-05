"""[es-leak / finca 2026-10-04] Jaime: 'tu venture actual' in a Spanish answer; a bare
'finca' missed the property domain so the raise-funding chip guard never ran."""


def test_finca_is_property():
    import antar_engine.domain_fit as df
    kw = df.__dict__.get("_DOMAINS") or df.__dict__.get("DOMAINS")
    if kw is None:   # module keeps the table under another name — find the property keywords
        kw = next(v for v in df.__dict__.values() if isinstance(v, dict) and "property" in v
                  and isinstance(v["property"], dict) and "kw" in v["property"])
    for w in ("finca", "hacienda", "fazenda", "chácara"):
        assert w in kw["property"]["kw"], w
