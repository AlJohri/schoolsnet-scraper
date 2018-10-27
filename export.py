import sys
import csv
import json
from scrape import REGIONS

for region_name in REGIONS.keys():
    region_slug = region_name.lower().replace(' ', '_')

    try:
        with open(f'data/{region_slug}.json') as f:
            rows = [json.loads(line) for line in f]
    except IOError:
        continue

    print(region_slug, len(rows))

    row_with_most_columns = max(rows, key=lambda x: len(x))
    fieldnames = list(row_with_most_columns.keys())

    with open(f'data/{region_slug}.csv', 'w') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
