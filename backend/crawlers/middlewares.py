import logging
import random
import time
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

# Pre-rotated pool in case fake-useragent fails
FALLBACK_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]


class RotateUserAgentMiddleware:
    """Rotate User-Agent per request to avoid blocking."""

    def __init__(self):
        try:
            self.ua = UserAgent(browsers=["chrome", "firefox", "safari"])
        except Exception:
            self.ua = None

    def process_request(self, request, spider):
        if self.ua:
            try:
                request.headers["User-Agent"] = self.ua.random
                return
            except Exception:
                pass
        request.headers["User-Agent"] = random.choice(FALLBACK_USER_AGENTS)

    def process_response(self, request, response, spider):
        return response


class CloudflareBypassMiddleware:
    """Detect Cloudflare challenge pages and automatically retry with Playwright.

    If Cloudflare is detected AND the spider has use_playwright=True, the
    middleware will automatically re-issue the request with Playwright enabled.
    Also adds automatic retry for transient Cloudflare 503s.
    """

    CF_CHALLENGE_KEYWORDS = [
        "just a moment",
        "cloudflare",
        "checking your browser",
        "cf-browser-verification",
        "challenge-platform",
        "__cf_chl_",
        "cdn-cgi/challenge-platform",
    ]

    MAX_CF_RETRIES = 3
    CF_RETRY_DELAY = 10  # seconds

    def process_response(self, request, response, spider):
        if response.status not in (403, 503, 429):
            return response

        body_text = response.text[:1000].lower()
        is_cf = any(kw in body_text for kw in self.CF_CHALLENGE_KEYWORDS)

        if not is_cf and response.status not in (429, 503):
            return response

        # ── Cloudflare challenge detected ──────────────────────
        if is_cf:
            spider.logger.warning(
                "☁️ Cloudflare detected on %s", response.url,
            )

            # Count previous CF retries for this URL to avoid infinite loop
            cf_retries = request.meta.get("_cf_retries", 0)
            if cf_retries >= self.MAX_CF_RETRIES:
                spider.logger.error(
                    "❌ Cloudflare max retries exceeded for %s", response.url
                )
                return response

            # Strategy 1: If spider has Playwright fallback, use it
            if getattr(spider, "use_playwright", False) and not request.meta.get("playwright"):
                spider.logger.info("🔄 Retrying with Playwright: %s", response.url)
                new_request = request.copy()
                new_request.meta["playwright"] = True
                new_request.meta["playwright_include_page"] = True
                new_request.meta["_cf_retries"] = cf_retries + 1
                return new_request

            # Strategy 2: Wait and retry (some CF challenges are transient)
            spider.logger.info("⏳ Waiting %ds before Cloudflare retry: %s",
                               self.CF_RETRY_DELAY, response.url)
            time.sleep(self.CF_RETRY_DELAY)
            new_request = request.copy()
            new_request.meta["_cf_retries"] = cf_retries + 1
            new_request.dont_filter = True
            return new_request

        # ── Rate limiting (429) / server error (503) ───────────
        if response.status == 429 or (response.status == 503 and not is_cf):
            retries_left = request.meta.get("_retry_times", 0)
            spider.logger.warning(
                "⏳ HTTP %s on %s (retries used: %s)",
                response.status, response.url, retries_left,
            )
            if retries_left < 3:
                wait = 10 * (retries_left + 1)
                spider.logger.info("   Waiting %ds and retrying...", wait)
                time.sleep(wait)
                new_request = request.copy()
                new_request.meta["_retry_times"] = retries_left + 1
                new_request.dont_filter = True
                return new_request

        return response