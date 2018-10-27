import re
import requests
import lxml.html
from urllib.parse import urlparse, parse_qs

s = requests.Session()

BASE_URL = "http://www.schoolsnet.com"

REGIONS = {
    "Scotland": 1, # 2713
    "Wales": 2, # 1734
    "Northern Ireland": 3, # 1137
    "East Anglia": 4, # 1423
    "Greater London": 5, # 3513
    "Midlands": 6,  # 5890
    "North": 7, # 4510
    "North West": 8, # 4038
    "South East": 9, # 6471
}

def get_boroughs(region_id):
    params = {"x": "16180339", "p_region_id": region_id,}
    response = s.get(f"{BASE_URL}/pls/hot_school/sn_search.obj_pls_schools_search_bymap", params=params)
    doc = lxml.html.fromstring(response.text)
    for a in doc.cssselect("#schoolsguide ol > li > a"):
        yield {
            'id': parse_qs(urlparse(a.get('href')).query)['p_lea_id'][0],
            'name': a.text,
            'url': BASE_URL + a.get('href'),
        }

def get_schools(region_id="", borough_id="", start_page=1):

    page = start_page

    while True:

        params = [
            ("schooltype", "0"),
            ("schooltype", "1"),
            ("schooltype", "2"),
            ("schooltype", "3"),
            ("schooltype", "5"),
            ("schooltype", "6"),
            ("schooltype", "8"),
            ("entry_gender", "-1"),
            ("gender_of_sixth_form", "-1"),
            ("type_of_institution", "-1"),
            ("a", "220708"),
            ("x", "16180339"),
            ("y", ""),
            ("p_region_id", region_id),
            ("p_lea_id", borough_id),
            ("search", "Search"),
            ("pageno", page)
        ]

        response = s.get(f"{BASE_URL}/uk-schools/search/search-schools.html", params=params)
        print(f"scraping page {page}:", response.url)

        if "Unfortunately, your search yielded no results." in response.text:
            return

        if "An unexpected problem" in response.text:
            doc = lxml.html.fromstring(response.text)
            error = doc.cssselect("#errorDetails")[0]
            raise Exception(error.text_content())

        doc = lxml.html.fromstring(response.text)

        meta_text = doc.cssselect('p.ViewResult')[0].getprevious().text_content()
        print(meta_text)
        meta = {
            "total": int(re.search(f"Your search yielded (\d+) schools", meta_text).groups(1)[0])
        }

        for el in doc.cssselect("table.leasearch dl"):
            row = {
                "name": el.cssselect("dt > a")[0].text,
                "url": BASE_URL + el.cssselect("dt > a")[0].get('href'),
                "full_address": " ".join([(x.text + " " + x.tail).replace("\n", " ").strip()
                    for x in el.cssselect("dd")]).replace("  ", " ").strip(),
            }
            yield row, meta

        page += 1

def parse_description_list(el):
    d = {}
    if el is None: return d
    for k, v in zip(el.cssselect("dt"), el.cssselect("dd")):
        if len(v.getchildren()) != 0: continue # skip nested
        key = k.text.replace(':', '')
        value = v.text
        d[key] = value
    return d

def select(el, selector, attr=None, fn=None):
    match = el.cssselect(selector)
    if match:
        if attr:
            return getattr(match[0], attr)
        else:
            return getattr(match[0], fn)()
    else:
        return None

def text(obj):
    return obj.text if obj else None

def parse_school_detail(doc):
    selector = '#contentcolumn div[itemprop="address"]'
    return {
        "name": select(doc, f'{selector} span[itemprop="name"]', attr='text'),
        "street_address": select(doc, f'{selector} span[itemprop="streetAddress"]', attr='text'),
        "locality": select(doc, f'{selector} span[itemprop="addressLocality"]', attr='text'),
        "postal_code": select(doc, f'{selector} span[itemprop="postalCode"]', attr='text'),
        "telephone": select(doc, f'{selector} span[itemprop="telephone"]', attr='text'),
        **parse_description_list(select(doc, selector, fn='getnext'))
    }

def get_school_detail(url):
    response = s.get(url)
    doc = lxml.html.fromstring(response.text)
    return parse_school_detail(doc)

if __name__ == "__main__":

    import json

    for region_name, region_id in REGIONS.items():

        region_slug = region_name.lower().replace(' ', '_')

        try:
            with open(f'data/{region_slug}.json', 'r') as f:
                schools = (json.loads(line) for line in f)
                schools = {x['url']:x for x in schools}
        except IOError:
            schools = {}

        with open(f'data/{region_slug}.json', 'a', buffering=1) as f:
            gen = get_schools(region_id=region_id)
            for i, (school, meta) in enumerate(gen):
                total = meta['total']
                if len(schools) == total:
                    print(f"[{region_slug}] scrape already finished. {len(schools)} downloaded and {total} schools total in search")
                    break

                if school['url'] in schools:
                    print(f"[{region_slug}] [{i} of {total}] {school['url']} already downloaded")
                    continue
                school_detail = get_school_detail(school['url'])
                school.update(school_detail)
                print(f"[{region_slug}] [{i} of {total}] {school['url']} downloaded")
                f.write(json.dumps(school) + "\n")
