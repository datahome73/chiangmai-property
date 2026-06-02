#!/usr/bin/env python3
"""Integration test for crawler stability enhancements."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['DATABASE_URL'] = 'sqlite:///cmproperty_test.db'
os.environ['SCRAPY_SETTINGS_MODULE'] = 'crawlers.settings'

import logging
logging.basicConfig(level=logging.WARNING, format='%(message)s')
logger = logging.getLogger('test')

passed = 0
failed = 0

def check(name, condition, detail=''):
    global passed, failed
    if condition:
        passed += 1
        print(f'  ✅ {name}  {detail}')
    else:
        failed += 1
        print(f'  ❌ {name}  {detail}')


# ── Test 1: Settings import ────────────────────
print('━━━ Test 1: Settings & config ━━━')
from crawlers.settings import DATABASE_URL, RETRY_TIMES, RETRY_HTTP_CODES
check('settings importable', True)
check('RETRY_TIMES=2', RETRY_TIMES == 2, str(RETRY_TIMES))
check('429 in RETRY_HTTP_CODES', 429 in RETRY_HTTP_CODES)
check('DATABASE_URL set', bool(DATABASE_URL))

# ── Test 2: ProxyAdapter ──────────────────────
print()
print('━━━ Test 2: ProxyAdapter retry + fallback ━━━')
from proxy_crawler.proxy_adapter import ProxyAdapter
adapter = ProxyAdapter(service='scrapingant')
html = adapter.fetch('https://www.example.com', max_retries=1, fallback_services=['scrapingbee'])
check('empty response without API key', html == '', f'{len(html)} bytes')

# Test: direct fetch from settings config
import httpx
try:
    resp = httpx.get('https://www.example.com', timeout=5)
    check('HTTP reachable', resp.status_code == 200)
except Exception:
    check('HTTP reachable', False)

# ── Test 3: Parsers import ────────────────────
print()
print('━━━ Test 3: Parser imports ━━━')
from proxy_crawler.parsers import DdpropertyParser, HipflatParser, FazwazParser, DotpropertyParser, PropertyhubParser
check('5 parsers importable', True)

parser = DdpropertyParser()
result = parser.parse_listing('''<html><body>
<h1>Test Title</h1>
<div class="price"><span>THB 15,000</span></div>
<div class="location">Nimman, Mueang, Chiang Mai</div>
<ul><li>2 Bedrooms</li><li>1 Bathroom</li><li>45 sq.m.</li></ul>
</body></html>''', 'https://www.ddproperty.com/detail/12345')
if result:
    check('parser extracts title', bool(result.get('title')))
    check('parser extracts price', result.get('price') == 15000.0)
    check('parser extracts location', bool(result.get('location_name')))
else:
    check('parser matched HTML structure', False, 'returned None - selector mismatch likely')

# ── Test 4: DatabasePipeline ──────────────────
print()
print('━━━ Test 4: DatabasePipeline write + upsert ━━━')
from crawlers.pipelines import DatabasePipeline
from crawlers.items import PropertyItem

pipeline = DatabasePipeline()
pipeline.open_spider(None)
check('pipeline connected', pipeline.engine is not None)

class MockSpider:
    logger = logging.getLogger('spider')

item = PropertyItem(source='test', source_id='int001', url='https://test.int/1',
    title='Integration Test', price=10000.0, listing_type='rent',
    bedrooms=1, bathrooms=1, floor_area=35.0, property_type='CONDO',
    location_name='Chiang Mai', district='Mueang', crawled_at='2026-06-02T00:00:00')
pipeline.process_item(item, MockSpider())

# Verify insert
from sqlalchemy import create_engine, text
engine = create_engine('sqlite:///cmproperty_test.db')
with engine.connect() as conn:
    count = conn.execute(text('SELECT COUNT(*) FROM properties')).scalar()
    row = conn.execute(text('SELECT title, price_rent FROM properties WHERE source_id=:sid'), {'sid': 'int001'}).fetchone()
check('item inserted', count >= 1)
check('title correct', row[0] == 'Integration Test')
check('price correct', row[1] == 10000.0)

# Update
item['price'] = 11000.0
item['title'] = 'Integration Test (Updated)'
pipeline.process_item(item, MockSpider())
with engine.connect() as conn:
    updated = conn.execute(text('SELECT title, price_rent FROM properties WHERE source_id=:sid'), {'sid': 'int001'}).fetchone()
check('upsert updated title', updated[0] == 'Integration Test (Updated)')
check('upsert updated price', updated[1] == 11000.0)

pipeline.close_spider(None)

# Test _ensure_connection
pipeline2 = DatabasePipeline()
pipeline2.open_spider(None)
check('re-connect after close', pipeline2.engine is not None)
pipeline2.close_spider(None)

# ── Test 5: Middleware ────────────────────────
print()
print('━━━ Test 5: Middleware ━━━')
from crawlers.middlewares import CloudflareBypassMiddleware
mw = CloudflareBypassMiddleware()
check('middleware max retries', mw.MAX_CF_RETRIES == 3)

# ── Summary ──────────────────────────────────
print()
print(f"{'━'*40}")
print(f"📊 结果: {passed} 通过, {failed} 失败")
if failed == 0:
    print("🎉 全部测试通过!")
else:
    print(f"⚠️  有 {failed} 个测试失败")
