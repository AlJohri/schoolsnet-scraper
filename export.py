import sys
import csv
import json
import pandas as pd

print('loading schools')
with open(f'data/schools.json', 'r') as f:
    schools = [json.loads(line) for line in f]

row_with_most_columns = max(schools, key=lambda x: len(x))
fieldnames = list(row_with_most_columns.keys())

print('writing data/schools.csv')
with open(f'data/schools.csv', 'w') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(schools)

print('writing data/schools.xlsx')
df = pd.read_csv('data/schools.csv')
df.to_excel('data/schools.xlsx', index=False)
