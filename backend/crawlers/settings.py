import os
import logging

logger = logging.getLogger(__name__)

BOT_NAME = "crawlers"

SPIDER_MODULES = ["crawlers.spiders"]
NEWSPIDER_MODULE = "crawlers.spiders"

# ─── Crawl responsibly ────────────────────────────────────
ROBOTSTXT_OBEY = False
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ─── Concurrency & throttling ─────────────────────────────
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 5.0
RANDOMIZE_DOWNLOAD_DELAY = True
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 5.0
AUTOTHROTTLE_MAX_DELAY = 60.0

# ─── Retry ────────────────────────────────────────────────
RETRY_TIMES = 2
RETRY_HTTP_CODES = [429, 500, 502, 503, 504]
DOWNLOAD_TIMEOUT = 30

# ─── Playwright (optional — for JS-rendered pages) ────────
# Only enable if Playwright browsers are installed.
# Install: playwright install chromium && playwright install-deps
try:
    from playwright.sync_api import sync_playwright
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True, timeout=5000)
    browser.close()
    p.stop()
    DOWNLOAD_HANDLERS = {
        "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    }
    TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
    PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": True, "timeout": 30000}
    logger.info("✅ Playwright enabled (Chromium available)")
except Exception as e:
    logger.warning("⚠️  Playwright disabled: %s", e)
    DOWNLOAD_HANDLERS = {}
    PLAYWRIGHT_LAUNCH_OPTIONS = {}

# ─── Middleware ───────────────────────────────────────────
DOWNLOADER_MIDDLEWARES = {
    "crawlers.middlewares.RotateUserAgentMiddleware": 400,
    "crawlers.middlewares.CloudflareBypassMiddleware": 450,
}

# ─── Pipelines ────────────────────────────────────────────
ITEM_PIPELINES = {
    "crawlers.pipelines.DuplicateFilterPipeline": 100,
    "crawlers.pipelines.FieldNormalizerPipeline": 200,
    "crawlers.pipelines.DatabasePipeline": 300,
}

# ─── Database ─────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(PROJECT_ROOT, 'cmproperty.db')}",
)
if DATABASE_URL and "mysql+" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("mysql+aiomysql://", "mysql+pymysql://").replace("mysql+asyncmy://", "mysql+pymysql://")

# ─── Other ────────────────────────────────────────────────
FEED_EXPORT_ENCODING = "utf-8"
COOKIES_ENABLED = True
TELNETCONSOLE_ENABLED = False
