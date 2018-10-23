import json
import csv

with open('schools.json') as f:
    rows = [json.loads(line) for line in f]

row_with_columns = max(rows, key=lambda x: len(x))
fieldnames = list(row_with_columns.keys())

with open('schools.csv', 'w') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
