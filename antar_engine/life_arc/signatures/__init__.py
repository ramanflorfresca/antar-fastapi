# Validated astrological signatures for Surface B predictions
#
# SIGNATURE_REGISTRY: maps signature names to their modules.
# get_enabled_signatures(): returns only signatures with enabled_in_library=True.
# get_library_version(): returns a cache-key-safe version string for all enabled sigs.

from . import wealth_jump, job_change, marriage, wealth_loss, business_fit, venture_timing

SIGNATURE_REGISTRY = {
    "wealth_jump":     wealth_jump,
    "job_change":      job_change,
    "marriage":        marriage,
    "wealth_loss":     wealth_loss,
    "business_fit":    business_fit,
    "venture_timing":  venture_timing,
}


def get_enabled_signatures() -> list:
    """Return list of (name, module) tuples with enabled_in_library=True."""
    return [
        (name, module) for name, module in SIGNATURE_REGISTRY.items()
        if getattr(module, "SIGNATURE_METADATA", {}).get("enabled_in_library", False)
    ]


def get_library_version() -> str:
    """
    Concat all enabled signature versions — used as cache key salt.
    When any signature version changes, cached results auto-invalidate.
    """
    parts = []
    for name, module in sorted(SIGNATURE_REGISTRY.items()):
        meta = getattr(module, "SIGNATURE_METADATA", {})
        if meta.get("enabled_in_library"):
            parts.append(f"{name}={meta.get('version', '?')}")
    return "|".join(parts) if parts else "empty"
