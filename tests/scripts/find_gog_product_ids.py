import asyncio
import re

import httpx
from loguru import logger

# ── 조회할 slug 목록 ──────────────────────────────────────────────────────────
SLUGS = [
    "the_secret_of_monkey_island_special_edition",
    "kings_quest_1_2_3",
    "monkey_island_2_special_edition_lechucks_revenge",
    "indiana_jones_and_the_fate_of_atlantis",
    "indiana_jones_and_the_last_crusade",
    "the_curse_of_monkey_island",
    "cyberpunk_2077",
    "the_witcher_3_wild_hunt",
]


async def fetch_product_id(client: httpx.AsyncClient, slug: str) -> dict:
    """GOG 상품 페이지 HTML에서 product_id를 추출한다."""
    url = f"https://www.gog.com/en/game/{slug}"
    try:
        resp = await client.get(url, follow_redirects=True, timeout=15.0)

        # 404 or redirected to different page
        if resp.status_code == 404:
            return {"slug": slug, "product_id": None, "title": None, "status": "NOT_FOUND"}

        html = resp.text

        # "id":"1207658878" 패턴 추출
        m = re.search(r'"id":"(\d{8,})"', html)
        product_id = m.group(1) if m else None

        # 상품명 추출
        title_m = re.search(r'<title>([^<]+)</title>', html)
        raw_title = title_m.group(1) if title_m else ""
        title = raw_title.replace(" on GOG.com", "").replace(" - GOG.com", "").strip()

        if product_id:
            return {"slug": slug, "product_id": product_id, "title": title, "status": "OK"}
        else:
            return {"slug": slug, "product_id": None, "title": title, "status": "ID_NOT_FOUND"}

    except Exception as e:
        return {"slug": slug, "product_id": None, "title": None, "status": f"ERROR: {e}"}


async def verify_price(client: httpx.AsyncClient, product_id: str, country_code: str = "US") -> str:
    """product_id로 실제 가격을 조회해 유효성을 검증한다."""
    url = f"https://api.gog.com/products/{product_id}/prices"
    try:
        resp = await client.get(url, params={"countryCode": country_code}, timeout=10.0)
        if resp.status_code != 200:
            return f"HTTP {resp.status_code}"

        data = resp.json()
        prices = data.get("_embedded", {}).get("prices", [])
        if not prices:
            return "가격 없음"

        entry = prices[0]
        base  = int(entry["basePrice"].split()[0]) / 100
        final = int(entry["finalPrice"].split()[0]) / 100
        currency = entry["currency"]["code"]

        if base == final:
            return f"{final:.2f} {currency}"
        else:
            discount = round((1 - final / base) * 100)
            return f"{final:.2f} {currency} ({discount}% 할인, 원가 {base:.2f})"

    except Exception as e:
        return f"ERROR: {e}"


async def main():
    logger.info(f"GOG product_id 조회 시작 — {len(SLUGS)}개 slug")
    print()

    results = []
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (compatible; DeReel/1.0)"},
    ) as client:
        for slug in SLUGS:
            result = await fetch_product_id(client, slug)

            # product_id 찾은 경우 가격도 검증
            if result["product_id"]:
                price_info = await verify_price(client, result["product_id"])
                result["price"] = price_info
            else:
                result["price"] = "-"

            results.append(result)

            # 결과 즉시 출력
            status_icon = "✅" if result["status"] == "OK" else "❌"
            print(
                f"{status_icon} {slug}\n"
                f"   product_id : {result['product_id'] or '없음'}\n"
                f"   title      : {result['title'] or '없음'}\n"
                f"   price      : {result.get('price', '-')}\n"
                f"   status     : {result['status']}\n"
            )

            await asyncio.sleep(0.5)  # rate limit 방지

    # ── targets.yaml 스니펫 자동 생성 ──────────────────────────────────────
    found = [r for r in results if r["status"] == "OK"]
    if found:
        print("=" * 60)
        print("# targets.yaml 복사용 스니펫")
        print("=" * 60)
        print("    products:")
        for r in found:
            print(f'      - product_id: "{r["product_id"]}"')
            print(f'        name: "{r["title"]}"')
            print(f'        target_price: 0.00  # 직접 설정 필요')
        print()

    not_found = [r for r in results if r["status"] != "OK"]
    if not_found:
        print("=" * 60)
        print("# 조회 실패 목록")
        print("=" * 60)
        for r in not_found:
            print(f"  - {r['slug']} → {r['status']}")


if __name__ == "__main__":
    asyncio.run(main())
