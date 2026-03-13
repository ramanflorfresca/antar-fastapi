#!/usr/bin/env python3
"""
seed_remedies.py
Populates Supabase tables with remedy data from JSON files.
Run: python seed_remedies.py
"""

import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def upsert_table(table, data, conflict_column='planet' if table == 'planet_remedies' else 'chakra_name' if table == 'chakra_protocols' else 'problem_area' if table == 'problem_planet_map' else 'age_range' if table == 'age_stages' else 'condition' if table == 'dasha_triggers' else 'transit_condition' if table == 'transit_rules' else 'id'):
    """
    Upsert data into the specified table.
    For tables without a natural unique key, we simply insert and let DB handle duplicates.
    """
    if data:
        # For tables with a natural unique key, use upsert; otherwise use insert.
        # You can customize the conflict resolution as needed.
        result = supabase.table(table).upsert(data, on_conflict=conflict_column).execute()
        print(f"Upserted {len(result.data)} rows into {table}")
    else:
        print(f"No data for {table}")

def main():
    # Planet remedies
    planets = load_json('data/planets.json')
    upsert_table('planet_remedies', planets, conflict_column='planet')

    # Chakra protocols
    chakras = load_json('data/chakras.json')
    upsert_table('chakra_protocols', chakras, conflict_column='chakra_name')

    # Dasha triggers
    dasha_rules = load_json('data/dasha_rules.json')
    upsert_table('dasha_triggers', dasha_rules, conflict_column='condition')

    # Transit rules
    transit_rules = load_json('data/transit_rules.json')
    upsert_table('transit_triggers', transit_rules, conflict_column='transit_condition')

    # Age stages
    age_stages = load_json('data/age_triggers.json')
    upsert_table('age_stages', age_stages, conflict_column='age_range')

    # Problem mapping
    problem_map = load_json('data/problem_mapping.json')
    upsert_table('problem_planet_map', problem_map, conflict_column='problem_area')

    # Safety rules
    safety_rules = load_json('data/safety_rules.json')
    upsert_table('safety_rules', safety_rules, conflict_column='id')  # uses id, so insert

if __name__ == '__main__':
    main()
