# patterns.py

def analyze_life_events(user_events, chart_data):
    """
    user_events: list of dicts with 'date', 'type', 'description'
    chart_data: D-1 chart
    Returns patterns: e.g., "Financial events tend to happen in Mercury-Jupiter periods."
    """
    # Group events by type
    patterns = []
    for event_type in set(e['type'] for e in user_events):
        events = [e for e in user_events if e['type'] == event_type]
        # For each event, find the dasha running at that time
        # Then see if there's a common planet or sign
        common_lords = []
        for e in events:
            # compute dasha at e['date'] (requires dasha calculation)
            # dummy
            common_lords.append('Venus')
        if common_lords:
            most_common = max(set(common_lords), key=common_lords.count)
            patterns.append(f"{event_type.capitalize()} events often occur during {most_common} periods.")
    return patterns

def apply_patterns_to_prediction(prediction, patterns):
    """Enhance a prediction with observed patterns."""
    if patterns:
        prediction['factors'].append(f"📊 Based on your history: {patterns[0]}")
    return prediction
