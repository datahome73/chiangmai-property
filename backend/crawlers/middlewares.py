import logging
import random
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
    """Detect Cloudflare challenge pages and log a warning.

    For sites behind Cloudflare, the spider should use Playwright
    (meta={'playwright': True}) to render JS challenges.
    """

    def process_response(self, request, response, spider):
        if response.status in (403, 503):
            body_text = response.text[:500].lower()
            if "just a moment" in body_text or "cloudflare" in body_text:
                spider.logger.warning(
                    "☁️ Cloudflare detected on %s — "
                    "re-run with Playwright: meta={'playwright': True}",
                    response.url,
                )
                # If spider has a playwright fallback, re-request with it
                if (
                    getattr(spider, "use_playwright", False)
                    and not request.meta.get("playwright")
                ):
                    spider.logger.info("🔄 Retrying with Playwright: %s", response.url)
                    new_request = request.copy()
                    new_request.meta["playwright"] = True
                    new_request.meta["playwright_include_page"] = True
                    return new_request
        return response
