#!/usr/bin/env python3
"""Test crawling with ScrapingAnt proxy on FazWaz"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['SCRAPINGANT_API_KEY'] = '2aa031d84c9c4781996faa541366a0f6'

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')

from proxy_crawler.proxy_adapter import ProxyAdapter
from proxy_crawler.parsers import FazwazParser

adapter = ProxyAdapter(service='scrapingant')

# Test FazWaz
html = adapter.fetch('https://www.fazwaz.com/property-for-rent/chiang-mai', max_retries=1)
if html:
    print(f'✅ FazWaz: got {len(html)} bytes')
    parser = FazwazParser()
    urls = parser.parse_list_urls(html, 'https://www.fazwaz.com/property-for-rent/chiang-mai')
    print(f'📋 Found {len(urls)} listing URLs')
    for u in urls[:3]:
        print(f'  {u}')
    if urls:
        detail_html = adapter.fetch(urls[0], max_retries=1)
        if detail_html:
            result = parser.parse_listing(detail_html, urls[0])
            if result:
                print(f'✅ Parsed: {result.get("title","?")}')
                print(f'   Price: {result.get("price")}, Beds: {result.get("bedrooms")}, Baths: {result.get("bathrooms")}')
else:
    print('❌ FazWaz failed')

# Test DDProperty
import ssl; ssl._create_default_https_context = ssl._create_unverified_context
html2 = adapter.fetch('https://www.ddproperty.com/en/rent/chiang-mai', max_retries=1)
if html2:
    print(f'✅ DDProperty: got {len(html2)} bytes')
    from proxy_crawler.parsers import DdpropertyParser
    parser2 = DdpropertyParser()
    urls2 = parser2.parse_list_urls(html2, 'https://www.ddproperty.com/en/rent/chiang-mai')
    print(f'📋 Found {len(urls2)} listing URLs')
    for u in urls2[:3]:
        print(f'  {u}')
else:
    print('❌ DDProperty failed')
