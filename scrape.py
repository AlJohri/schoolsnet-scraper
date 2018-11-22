import re
import requests
import requests_cache
from requests.adapters import HTTPAdapter
import lxml.html
from urllib.parse import urlparse, parse_qs

adapter = HTTPAdapter(max_retries=5)

session = requests.Session()
cached_session = requests_cache.core.CachedSession()

session.mount('http://', adapter)
cached_session.mount('http://', adapter)

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
    "South West": 10,
}

def get_boroughs(region_id):
    params = {"x": "16180339", "p_region_id": region_id,}
    response = session.get(f"{BASE_URL}/pls/hot_school/sn_search.obj_pls_schools_search_bymap", params=params)
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

        response = session.get(f"{BASE_URL}/uk-schools/search/search-schools.html", params=params)
        print(f"scraping page {page}:", response.url)

        if "Unfortunately, your search yielded no results." in response.text:
            return

        if "An unexpected problem" in response.text:
            doc = lxml.html.fromstring(response.text)
            error = doc.cssselect("#errorDetails")[0]
            raise Exception(error.text_content())

        response.raise_for_status()

        doc = lxml.html.fromstring(response.text)

        # meta_text = doc.cssselect('p.ViewResult')[0].getprevious().text_content()
        meta_text = doc.cssselect('#contentcolumn h3')[0].getnext().text_content()
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
        key = k.text.replace(':', '').lower().replace(' ', '_')
        if key in ['email', 'website']:
            d[key] = v.cssselect('a')[0].get('href').replace('mailto:', '')
        elif key in ['number_of_students']:
            d[key] = int(v.text.replace(',', ''))
        elif key in ['last_inspection']:
            d[key] = v.text.replace('.', '')
        elif key in ['authority']:
            d['borough'] = v.text
        else:
            d[key] = v.text_content()
    return d

def select(el, selector, attr=None, fn=None):
    match = el.cssselect(selector)
    if match:
        if attr:
            return getattr(match[0], attr)
        else:
            return getattr(match[0], fn)()

def parse_school_detail(doc):
    selector = '#contentcolumn div[itemprop="address"]'
    return {
        "name": select(doc, f'{selector} span[itemprop="name"]', attr='text'),
        "street_address": select(doc, f'{selector} span[itemprop="streetAddress"]', attr='text'),
        "locality": select(doc, f'{selector} span[itemprop="addressLocality"]', attr='text'),
        "postal_code": select(doc, f'{selector} span[itemprop="postalCode"]', attr='text'),
        "telephone": select(doc, f'{selector} span[itemprop="telephone"]', attr='text'),
        "school_type": doc.cssselect('div[itemtype="https://schema.org/breadcrumb"] > a span')[-1].text,
        "last_updated": re.search(r'last updated here on (.*)', doc.cssselect(selector)[0].getnext().getnext().text).groups(1)[0],
        **parse_description_list(doc.cssselect(selector)[0].getnext())
    }

def get_school_detail(url):
    response = cached_session.get(url)
    if "An unexpected problem" in response.text:
        doc = lxml.html.fromstring(response.text)
        error = doc.cssselect("#errorDetails")[0]
        raise Exception(error.text_content())
    response.raise_for_status()
    if response.url == "http://www.schoolsnet.com/uk-schools/schoolHome.jsp":
        raise Exception(f"was redirected back to homepage when downloading {url}")
    doc = lxml.html.fromstring(response.text)
    return parse_school_detail(doc)

if __name__ == "__main__":

    import json

    try:
        with open(f'data/schools.json', 'r') as f:
            schools = (json.loads(line) for line in f)
            schools = {x['url']:x for x in schools}
    except IOError:
        schools = {}

    with open(f'data/schools.json', 'a', buffering=1) as f:
        for region_name, region_id in REGIONS.items():
            num_schools_in_region = sum([1 for x in schools.values() if x['region'] == region_name])
            gen = get_schools(region_id=region_id)
            for i, (school, meta) in enumerate(gen):
                total = meta['total']
                if num_schools_in_region == total:
                    print(f"[{region_name}] scrape already finished. {num_schools_in_region} downloaded and {total} schools total in search")
                    break

                if school['url'] in schools:
                    print(f"[{region_name}] [{i} of {total}] {school['url']} already downloaded")
                    continue
                school_detail = get_school_detail(school['url'])
                school.update(school_detail)
                school['region'] = region_name
                print(f"[{region_name}] [{i} of {total}] {school['url']} downloaded")
                f.write(json.dumps(school) + "\n")
