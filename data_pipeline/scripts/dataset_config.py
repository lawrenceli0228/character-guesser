"""Size of the extended dataset, shared by the fetch and roster-building scripts."""

# Final number of entries per kind, including the hand-curated roster.
TARGET_REAL = 350
TARGET_FICTIONAL = 150

# Fetch facts for more candidates than needed: some are skipped by
# build_auto_roster.py when Wikidata has too little usable information.
FETCH_BUFFER = 1.4
