import argparse
import asyncio
from datetime import datetime, timedelta, timezone

import yaml
from loguru import logger

from dereel.core.alert_history import AlertHistory
from dereel.core.comparator import Comparator
from dereel.core.notifier import Notifier
from dereel.core.storage import JsonStorage
from dereel.crawlers.apple_refurb import AppleRefurbCrawler
from dereel.crawlers.steam import SteamCrawler

CRAWLER_REGISTRY = {
    "apple_refurb": AppleRefurbCrawler,
    "steam":        SteamCrawler,
}


def should_crawl(storage: JsonStorage, key: str, interval_hours: int) -> bool:
    """마지막 크롤링 시각 기준으로 interval_hours가 경과했는지 확인."""
    last = storage.get_last_crawled_at(key)
    if last is None:
        return True
    return datetime.now(timezone.utc) - last >= timedelta(hours=interval_hours)


async def run(crawl_type: str) -> None:
    with open("config/targets.yaml") as f:
        config = yaml.safe_load(f)

    storage = JsonStorage()
    alert_history = AlertHistory(storage)
    notifier = Notifier()
    comparator = Comparator(storage, alert_history, notifier)

    targets = [
        t for t in config["targets"]
        if t.get("enabled", True) and t.get("type", "stock") == crawl_type
    ]

    if not targets:
        logger.info(f"[{crawl_type}] 실행 대상 없음")
        return

    logger.info(f"[{crawl_type}] 대상 {len(targets)}건 확인 중")

    for target in targets:
        site = target["site"]
        url = target.get("url", "")
        dry_run = target.get("dry_run", False)
        interval_hours = target.get("interval_hours", 4)

        # site + url 조합으로 스케줄 키 생성 (같은 사이트의 다른 URL 구분)
        schedule_key = f"{site}:{url}"

        if not should_crawl(storage, schedule_key, interval_hours):
            logger.info(f"[{site}] 스킵 — 아직 {interval_hours}시간 미경과 ({url})")
            continue

        crawler_cls = CRAWLER_REGISTRY.get(site)
        if not crawler_cls:
            logger.warning(f"등록되지 않은 크롤러: {site}")
            continue

        try:
            async with crawler_cls() as crawler:
                results = await crawler.fetch(url)
        except Exception as e:
            logger.error(f"[{site}] 크롤링 실패 — {e}")
            await notifier.send(
                f"🚨 [{site}] 크롤링 실패\n\n🔗 {url}\n❗ {e}",
                dry_run=dry_run,
            )
            continue

        crawler_type = target.get("type", "stock")
        if crawler_type == "price":
            products = target.get("products", [])
            await comparator.compare_price(site, results, products, dry_run=dry_run)
        else:
            await comparator.compare_stock(site, results, dry_run=dry_run)

        storage.save_crawled_at(schedule_key, datetime.now(timezone.utc))

    logger.info(f"[{crawl_type}] 전체 크롤링 완료 ✅")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--type",
        choices=["stock", "price"],
        default="stock",
        help="실행할 크롤러 타입 (stock | price)",
    )
    args = parser.parse_args()
    asyncio.run(run(args.type))
