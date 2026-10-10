# Retrodiction ground truth (private — CSVs are gitignored)

`people.csv`: id,date,time,tz,lat,lon,rating   (local birth date/time, tz = hours east of UTC)
`events.csv`: person,type,date,tol_days        (type: business_start | career_start | relationship_began | relationship_ended)

Run: `python -I scripts/retrodiction/run.py` (needs pyswisseph). Rules are pre-registered in the script header.
