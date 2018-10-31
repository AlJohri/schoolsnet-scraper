import json
import pprint
import textwrap
import traceback
from scrape import get_school_detail

print('loading schools')
with open(f'data/schools.json', 'r') as f:
    schools = [json.loads(line) for line in f]

updated_schools = []
for i, school in enumerate(schools):
    print(f'[{i} of {len(schools)}] rescraping', school['url'])
    try:
        school_detail = get_school_detail(school['url'])
    except Exception:
        print("ERRORRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR")
        traceback.print_exc()
        school_detail = {}
    school = {
        'name': school['url'], **school_detail, 'url': school['url']}
    updated_schools.append(school)

with open(f'data/schools.json', 'w') as f:
    for school in updated_schools:
        f.write(json.dumps(school) + "\n")
