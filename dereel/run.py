import argparse
import asyncio

import yaml
from loguru import logger

from dereel.core.alert_history import AlertHistory
from dereel.core.comparator import Comparator
from dereel.core.notifier import Notifier
from dereel.core.storage import JsonStorage
from dereel.crawlers.apple_refurb import AppleRefurbCrawler
from dereel.crawlers.gog import GogCrawler
from dereel.crawlers.steam import SteamCrawler

CRAWLER_REGISTRY = {
    "apple_refurb": AppleRefurbCrawler,
    "steam": SteamCrawler,
    "gog": GogCrawler,
}


async def run(type_filter: str | None = None) -> None:
    with open("config/targets.yaml") as f:
        config = yaml.safe_load(f)

    storage = JsonStorage()
    alert_history = AlertHistory(storage)
    notifier = Notifier()
    comparator = Comparator(storage, alert_history, notifier)

    for target in config["targets"]:
        site = target["site"]
        target_type = target.get("type", "stock")
        dry_run = target.get("dry_run", False)
        enabled = target.get("enabled", True)

        # --type 인자로 필터링
        if type_filter and target_type != type_filter:
            logger.debug(f"[{site}] type={target_type} — '{type_filter}' 필터로 스킵")
            continue

        if not enabled:
            logger.debug(f"[{site}] 비활성화 — 스킵")
            continue

        crawler_cls = CRAWLER_REGISTRY.get(site)
        if not crawler_cls:
            logger.warning(f"등록되지 않은 크롤러: {site}")
            continue

        try:
            async with crawler_cls() as crawler:
                if target_type == "stock":
                    url = target["url"]
                    results = await crawler.fetch(url)
                    await comparator.compare_stock(site, results, dry_run=dry_run)

                elif target_type == "price":
                    products = target.get("products", [])
                    currency = target.get("currency", "USD")
                    results = await crawler.fetch_products(products, currency=currency)
                    await comparator.compare_price(site, results, products, dry_run=dry_run)

        except Exception as e:
            logger.error(f"[{site}] 크롤링 실패 — {e}")
            await notifier.send(
                f"🚨 [{site}] 크롤링 실패\n\n❗ {e}",
                dry_run=dry_run,
            )

    logger.info("전체 크롤링 완료 ✅")


def main() -> None:
    parser = argparse.ArgumentParser(description="DeReel 크롤러")
    parser.add_argument(
        "--type",
        dest="type_filter",
        choices=["stock", "price"],
        default=None,
        help="실행할 타겟 타입 (stock / price). 생략하면 전체 실행.",
    )
    args = parser.parse_args()
    asyncio.run(run(type_filter=args.type_filter))


if __name__ == "__main__":
    main()