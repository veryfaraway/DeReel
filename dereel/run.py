import argparse
import asyncio
from datetime import UTC, datetime

import yaml  # type: ignore[import-untyped]
from loguru import logger

from dereel.core.alert_history import AlertHistory
from dereel.core.comparator import Comparator
from dereel.core.notifier import Notifier
from dereel.core.settings import settings
from dereel.core.storage import get_storage
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

    storage = get_storage(settings.storage_type, data_dir=settings.data_dir)
    alert_history = AlertHistory(storage)
    notifier = Notifier()
    comparator = Comparator(storage, alert_history, notifier)

    for target in config["targets"]:
        site = target["site"]
        target_type = target.get("type", "stock")
        dry_run = target.get("dry_run", False)
        enabled = target.get("enabled", True)

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

        # interval_hours 스케줄 체크
        interval_hours: float = target.get("interval_hours", 1)
        url_key: str = target.get("url", "")
        schedule_key = f"{site}:{url_key}" if url_key else site
        last_crawled = storage.get_last_crawled_at(schedule_key)
        if last_crawled is not None:
            elapsed_hours = (datetime.now(UTC) - last_crawled).total_seconds() / 3600
            if elapsed_hours < interval_hours:
                logger.debug(
                    f"[{site}] interval_hours={interval_hours} 미경과 "
                    f"({elapsed_hours:.1f}h/{interval_hours}h) — 스킵"
                )
                continue

        try:
            async with crawler_cls() as crawler:  # type: ignore[abstract]
                if target_type == "stock":
                    url = target["url"]
                    results = await crawler.fetch(url)
                    await comparator.compare_stock(site, results, dry_run=dry_run)

                elif target_type == "price":
                    products = target.get("products", [])
                    currency = target.get("currency", "USD")
                    results = await crawler.fetch_products(products, currency=currency)  # type: ignore[attr-defined]
                    await comparator.compare_price(site, results, products, dry_run=dry_run)

            storage.save_crawled_at(schedule_key, datetime.now(UTC))
            storage.reset_failures(site)

        except Exception as e:
            failures_count = storage.increment_failures(site, str(e))
            logger.error(f"[{site}] 크롤링 실패 ({failures_count}회 연속) — {e}")

            if failures_count >= 3:
                await notifier.send(
                    f"🚨 [DeReel 경보] 크롤러 연속 실패\n\n"
                    f"🌐 사이트: {site}\n"
                    f"💥 오류: {e}\n"
                    f"🔁 연속 실패 횟수: {failures_count}회",
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
