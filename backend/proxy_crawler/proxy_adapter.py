"""
代理 API 通用适配器 — 支持多种云爬虫代理服务

支持的服务:
  - ScrapingAnt    (默认推荐) https://scrapingant.com
  - ScrapingBee    https://www.scrapingbee.com
  - ScrapingFish   https://scrapingfish.com
  - ZenRows        https://www.zenrows.com
  - Crawlbase      https://crawlbase.com

用法:
  adapter = ProxyAdapter(service="scrapingant", api_key="xxx")
  html = adapter.fetch("https://example.com")
"""

import os
import time
import json
import logging
from urllib.parse import urlencode
from typing import Optional

logger = logging.getLogger("proxy-adapter")


class ProxyAdapter:
    """Generic proxy API adapter with built-in retry and error handling."""

    SERVICES = {
        "scrapingant": {
            "base_url": "https://api.scrapingant.com/v2/general",
            "param_name": "url",
            "extra_params": {},  # No browser mode (site blocks headless browsers)
            "header_name": "x-api-key",
            "response_field": "content",
            "rate_limit": 2.0,
        },
        "scrapingbee": {
            "base_url": "https://app.scrapingbee.com/api/v1",
            "param_name": "url",
            "extra_params": {"render_js": "true", "premium_proxy": "true"},
            "response_field": None,                # raw HTML response
            "rate_limit": 1.0,
        },
        "scrapingfish": {
            "base_url": "https://scrapingfish.com/api/v1",
            "param_name": "url",
            "extra_params": {"render": "true"},
            "response_field": "data",
            "rate_limit": 1.0,
        },
        "zenrows": {
            "base_url": "https://api.zenrows.com/v1",
            "param_name": "url",
            "extra_params": {"js_render": "true", "antibot": "true", "premium_proxy": "true"},
            "response_field": None,
            "rate_limit": 1.0,
        },
        "crawlbase": {
            "base_url": "https://api.crawlbase.com",
            "param_name": "url",
            "extra_params": {"render": "true"},
            "response_field": "body",
            "rate_limit": 1.0,
        },
    }

    def __init__(self, service: str = "scrapingant", api_key: Optional[str] = None):
        """
        Args:
            service: 服务名称 (scrapingant / scrapingbee / scrapingfish / zenrows / crawlbase)
            api_key: API key，默认从环境变量读取
        """
        if service not in self.SERVICES:
            raise ValueError(f"不支持的服务: {service}，可选: {', '.join(self.SERVICES.keys())}")

        self.service = service
        self.config = self.SERVICES[service]

        # API key 优先级: 参数 > 环境变量
        env_var_map = {
            "scrapingant": "SCRAPINGANT_API_KEY",
            "scrapingbee": "SCRAPINGBEE_API_KEY",
            "scrapingfish": "SCRAPINGFISH_API_KEY",
            "zenrows": "ZENROWS_API_KEY",
            "crawlbase": "CRAWLBASE_API_KEY",
        }
        self.api_key = api_key or os.environ.get(env_var_map[service], "")

        if not self.api_key:
            logger.warning(
                "⚠️  未设置 %s API Key！\n"
                "   请设置环境变量 %s=your_key\n"
                "   或在代码中传入 ProxyAdapter(service='%s', api_key='xxx')",
                service, env_var_map[service], service,
            )

        self._last_request = 0.0
        self.session = None

    def fetch(self, url: str, wait_for_selector: Optional[str] = None) -> str:
        """
        通过代理 API 获取 URL 的 HTML 内容。

        Args:
            url: 目标 URL
            wait_for_selector: ScrapingAnt 专用 - 等待 CSS 选择器出现后再返回

        Returns:
            HTML 字符串，失败返回空字符串
        """
        if not self.api_key:
            logger.error("❌ API Key 未设置，无法请求 %s", url)
            return ""

        # Rate limiting
        elapsed = time.time() - self._last_request
        if elapsed < self.config["rate_limit"]:
            time.sleep(self.config["rate_limit"] - elapsed)
        self._last_request = time.time()

        # Build request params
        params = {
            self.config["param_name"]: url,
        }

        # Build headers
        headers = {}
        header_name = self.config.get("header_name")
        if header_name:
            headers[header_name] = self.api_key
        else:
            params["api_key"] = self.api_key

        params.update(self.config.get("extra_params", {}))

        if wait_for_selector and self.service == "scrapingant":
            params["wait_for_selector"] = wait_for_selector

        # Make request
        import httpx
        request_url = f"{self.config['base_url']}?{urlencode(params)}"

        try:
            with httpx.Client(timeout=120.0, follow_redirects=True) as client:
                resp = client.get(request_url, headers=headers)
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "")
                response_field = self.config.get("response_field")

                if response_field and "application/json" in content_type:
                    data = resp.json()
                    html = data.get(response_field, "") or resp.text
                else:
                    html = resp.text

                if not html:
                    logger.warning("⚠️  空响应: %s", url)
                    return ""

                logger.info("✅ 成功获取 %s (%d bytes)", url.split("//")[1][:50], len(html))
                return html

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            logger.error("❌ HTTP %s: %s", status, url)
            if status == 409:
                logger.warning("   409 Conflict — 速率限制，等待 30 秒后重试...")
                time.sleep(30)
                # One retry
                try:
                    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
                        resp = client.get(request_url, headers=headers)
                        resp.raise_for_status()
                        content_type = resp.headers.get("content-type", "")
                        response_field = self.config.get("response_field")
                        if response_field and "application/json" in content_type:
                            return resp.json().get(response_field, "") or resp.text
                        return resp.text
                except Exception as e2:
                    logger.error("❌ 重试仍失败: %s", e2)
            if self.service == "scrapingant" and status == 402:
                logger.error("   ScrapingAnt 免费额度已用完！升级套餐或等待下个月重置。")
            return ""

        except Exception as e:
            logger.error("❌ 请求失败 %s: %s", url, e)
            return ""


def register_proxy_service(name: str, config: dict):
    """注册自定义代理服务（扩展支持其他服务）"""
    ProxyAdapter.SERVICES[name] = config
