# HOW_TO_ADD_CRAWLER.md
# DeReel — 새 크롤러 추가 가이드

> **버전:** v0.1.0
> **작성일:** 2026-03-31
> **작성자:** 한섭
> **연관 문서:** [ARCHITECTURE.md](./ARCHITECTURE.md) | [CRAWLING_STRATEGY.md](./CRAWLING_STRATEGY.md) | [CONVENTIONS.md](./CONVENTIONS.md)

---

## 개요

DeReel은 **플러그인 구조**로 설계되어 있어, 새 크롤러를 추가할 때  
기존 코드를 수정하지 않고 **파일 추가 + 설정 변경**만으로 확장할 수 있다.

새 크롤러 추가는 총 **7단계**로 이루어진다.

```
1단계  사이트 사전 조사
2단계  크롤러 파일 생성 (BaseCrawler 상속)
3단계  fetch() 구현 — 데이터 수집
4단계  parse() 구현 — 데이터 정규화
5단계  format_message() 구현 — 알림 메시지
6단계  targets.yaml 등록
7단계  테스트 작성 및 드라이런 검증
```

---

## 1단계 — 사이트 사전 조사

크롤러를 짜기 전에 반드시 아래 항목을 확인한다.

### 1.1 체크리스트

```
□ robots.txt 확인
    → https://{사이트}/robots.txt 직접 열어보기
    → Disallow 경로에 감시 대상 URL이 포함되어 있는지 확인

□ 데이터 노출 방식 확인
    → 브라우저 개발자 도구 → Network 탭 → XHR/Fetch 필터
    → JSON API가 있으면 API 방식 우선 선택
    → 없으면 HTML 파싱 방식

□ 로그인 필요 여부
    → 로그인 필요 페이지는 수집 대상 제외 (Out of Scope)

□ Rate Limit 확인
    → 공식 API는 문서에서 확인
    → 비공식은 빠른 연속 요청 시 429 반환 여부로 추정

□ 사이트 식별자(site_name) 결정
    → snake_case, 영문 소문자
    → targets.yaml 키와 동일하게 사용
    → 예: "gog", "epic", "playstation_store"
```

### 1.2 수집 방식 결정 기준

```
공식 API 있음
    └─→ API 방식 (httpx)

공식 API 없음 + 정적 HTML
    └─→ HTML 파싱 방식 (httpx + BeautifulSoup)

공식 API 없음 + JS 렌더링 필수
    └─→ 헤드리스 브라우저 방식 (Playwright)
```

---

## 2단계 — 크롤러 파일 생성

`dereel/crawlers/` 디렉토리에 `{site_name}.py` 파일을 생성한다.

```bash
touch dereel/crawlers/{site_name}.py
```

### 기본 골격 (복사해서 시작)

```python
# dereel/crawlers/{site_name}.py
"""
{사이트 전체 이름} 크롤러

수집 방식: {API / HTML 파싱 / Playwright}
대상 URL:  {엔드포인트 또는 페이지 URL}
공식 여부: {공식 API / 비공식 API / HTML 파싱}
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from typing import Any

import httpx

from dereel.core.base_crawler import BaseCrawler
from dereel.models.price_result import PriceResult   # 또는 StockResult
from dereel.core.message_formatter import fmt_price, fmt_datetime

# ── 상수 ──────────────────────────────────────────
BASE_URL     = "https://..."
TIMEOUT      = 30.0
MIN_DELAY    = 3.0
MAX_DELAY    = 8.0


class {SiteName}Crawler(BaseCrawler):
    """
    {사이트명} 크롤러

    감시 대상:
        - {설명}
    알림 트리거:
        - {설명}
    """

    site_name = "{site_name}"   # targets.yaml 키와 동일

    # ------------------------------------------------------------------
    # 3단계: fetch()
    # ------------------------------------------------------------------
    async def fetch(self) -> Any:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 4단계: parse()
    # ------------------------------------------------------------------
    def parse(self, raw_data: Any) -> list[PriceResult]:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 5단계: format_message()
    # ------------------------------------------------------------------
    def format_message(self, diff: dict) -> str:
        raise NotImplementedError
```

---

## 3단계 — fetch() 구현

원본 데이터를 가져오는 메서드다.
**네트워크 요청만 담당하고, 파싱은 하지 않는다.**

### 패턴 A: JSON API (httpx)

```python
async def fetch(self) -> dict:
    """
    {사이트명} API에서 원본 JSON 응답을 반환한다.
    실패 시 예외를 raise — BaseCrawler.run()이 try/except로 처리.
    """
    params = {
        "country": "KR",
        "language": "ko",
    }
    async with httpx.AsyncClient(
        headers=self._headers(),
        timeout=TIMEOUT,
    ) as client:
        response = await client.get(BASE_URL, params=params)
        response.raise_for_status()
        return response.json()
```

### 패턴 B: 복수 제품 순차 조회 (API + 딜레이)

```python
async def fetch(self) -> list[dict]:
    """
    targets.yaml의 products 목록을 순차적으로 조회한다.
    요청 사이 랜덤 딜레이로 Rate Limit 회피.
    """
    results  = []
    products = self.config.get("products", [])

    async with httpx.AsyncClient(headers=self._headers(), timeout=TIMEOUT) as client:
        for i, product in enumerate(products):
            try:
                url      = f"{BASE_URL}/{product['product_id']}"
                response = await client.get(url)
                response.raise_for_status()
                results.append({
                    "product_id": product["product_id"],
                    "name":       product["name"],
                    "data":       response.json(),
                })
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"{self.site_name} | HTTP {e.response.status_code} "
                    f"- {product['product_id']} 스킵"
                )
            # 마지막 제품 이후에는 딜레이 생략
            if i < len(products) - 1:
                await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    return results
```

### 패턴 C: Playwright (JS 렌더링 필요)

```python
from playwright.async_api import async_playwright

async def fetch(self) -> list[dict]:
    results  = []
    products = self.config.get("products", [])

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=self._headers()["User-Agent"],
            locale="ko-KR",
        )
        for product in products:
            page = await context.new_page()
            try:
                await page.goto(
                    f"https://site.com/dp/{product['product_id']}",
                    wait_until="domcontentloaded",
                    timeout=30_000,
                )
                await page.wait_for_timeout(random.randint(2000, 4000))
                results.append({
                    "product_id": product["product_id"],
                    "html":       await page.content(),
                })
            finally:
                await page.close()

        await browser.close()
    return results
```

---

## 4단계 — parse() 구현

원본 데이터를 `PriceResult` 또는 `StockResult` 리스트로 변환한다.
**네트워크 요청 없이 순수 변환 로직만 작성한다.**

```python
def parse(self, raw_data: list[dict]) -> list[PriceResult]:
    """
    API 응답 → PriceResult 리스트 변환.
    필드 누락 시 구조 변경 경보를 발생시킨다.
    """
    results = []

    for item in raw_data:
        try:
            data       = item["data"]
            price_info = data["price_overview"]   # ← 구조 변경 시 KeyError 발생

            original   = price_info["initial"]    # 정가
            current    = price_info["final"]      # 현재가
            discount   = price_info["discount_percent"]

            results.append(PriceResult(
                site            = self.site_name,
                product_id      = item["product_id"],
                name            = item["name"],
                price           = current,
                original_price  = original,
                discount_pct    = float(discount),
                currency        = "KRW",
                original_amount = current,
                url             = f"https://site.com/app/{item['product_id']}",
                fetched_at      = datetime.now(timezone.utc),
            ))

        except KeyError as e:
            # 구조 변경 감지 → 경보 발송 후 해당 아이템 스킵
            self._alert_structure_change(
                expected_field=str(e),
                actual_keys=list(item.get("data", {}).keys()),
            )

    return results
```

### parse() 작성 원칙

```
✅ 반드시 지킬 것
    - KeyError, TypeError는 반드시 try/except로 처리
    - 파싱 실패한 개별 아이템은 스킵 (전체 중단 금지)
    - 구조 변경 감지 시 _alert_structure_change() 호출
    - 가격은 원화 기준 원 단위 정수로 저장

❌ 하면 안 되는 것
    - parse() 안에서 HTTP 요청 금지
    - 전역 상태(파일 I/O, DB) 접근 금지
    - 파싱 실패 시 예외를 밖으로 전파 금지
```

---

## 5단계 — format_message() 구현

알림 메시지 문자열을 반환한다.
`NOTIFICATION_SPEC.md`의 포맷 가이드를 따른다.

```python
def format_message(self, diff: dict) -> str:
    """
    가격 하락 알림 메시지를 생성한다.

    Args:
        diff: {
            "result":       PriceResult,
            "alert_type":   "price" | "discount" | "free",
            "target_price": int | None,
            "threshold":    float | None,
        }
    """
    result: PriceResult = diff["result"]
    alert_type: str     = diff["alert_type"]

    if alert_type == "price":
        return (
            f"💸 [{self._display_name()}] 가격 알림\n\n"
            f"🎯 {result.name}\n"
            f"💰 현재가: {fmt_price(result.price)} "
            f"(목표가: {fmt_price(diff['target_price'])})\n"
            f"📉 정가 대비: -{result.discount_pct:.0f}% "
            f"({fmt_price(result.original_price)} → {fmt_price(result.price)})\n"
            f"🔗 {result.url}\n\n"
            f"🕐 {fmt_datetime(result.fetched_at)}"
        )

    if alert_type == "discount":
        return (
            f"📉 [{self._display_name()}] 할인 알림\n\n"
            f"🎯 {result.name}\n"
            f"🔥 할인율: -{result.discount_pct:.0f}% "
            f"(설정 임계값: -{diff['threshold']:.0f}%)\n"
            f"💰 {fmt_price(result.original_price)} → {fmt_price(result.price)}\n"
            f"🔗 {result.url}\n\n"
            f"🕐 {fmt_datetime(result.fetched_at)}"
        )

    # Fallback
    return f"[{self._display_name()}] {result.name} 알림\n🔗 {result.url}"

def _display_name(self) -> str:
    """Telegram 메시지에 표시할 사이트 이름"""
    return "사이트명"   # 예: "GOG", "Epic Games"
```

---

## 6단계 — targets.yaml 등록

```yaml
crawlers:
  # ... 기존 크롤러들 ...

  # ── {사이트 전체 이름} ─────────────────────────────
  {site_name}:
    enabled: false            # ← 처음에는 반드시 false로 시작
    interval_hours: 3
    products:
      - product_id: "test-id-001"
        name: "테스트 제품명"
        target_price: 10000
        alert_threshold: 50.0
```

드라이런 검증 후 `enabled: true`로 변경한다.

---

## 7단계 — 테스트 작성 및 드라이런 검증

### 7.1 단위 테스트 작성

```python
# tests/crawlers/test_{site_name}.py
import pytest
import respx
import httpx
from dereel.crawlers.{site_name} import {SiteName}Crawler


@pytest.fixture
def crawler():
    return {SiteName}Crawler(config={
        "products": [
            {"product_id": "test-001", "name": "테스트 제품", "target_price": 10000}
        ]
    })

@pytest.fixture
def mock_response():
    return { ... }   # 실제 API 응답 구조 참고


class TestFetch:

    @respx.mock
    async def test_정상_응답(self, crawler, mock_response):
        respx.get(BASE_URL).mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        result = await crawler.fetch()
        assert result is not None

    @respx.mock
    async def test_HTTP_429_예외처리(self, crawler):
        respx.get(BASE_URL).mock(return_value=httpx.Response(429))
        with pytest.raises(httpx.HTTPStatusError):
            await crawler.fetch()


class TestParse:

    def test_정상_파싱(self, crawler, mock_response):
        results = crawler.parse([{"product_id": "test-001", "data": mock_response}])
        assert len(results) == 1
        assert results[0].price > 0

    def test_구조_변경_스킵(self, crawler):
        """필드 누락 시 스킵 — 예외 전파 없음"""
        results = crawler.parse([{"product_id": "test-001", "data": {}}])
        assert results == []


class TestFormatMessage:

    def test_가격_알림_키워드_포함(self, crawler):
        from dereel.models.price_result import PriceResult
        from datetime import datetime, timezone

        result = PriceResult(
            site="test", product_id="001", name="테스트 게임",
            price=9900, original_price=39800, discount_pct=75.0,
            currency="KRW", original_amount=9900,
            url="https://example.com",
            fetched_at=datetime.now(timezone.utc),
        )
        msg = crawler.format_message({
            "result": result, "alert_type": "price", "target_price": 10000,
        })
        assert "테스트 게임" in msg
        assert "9,900" in msg
        assert "75" in msg
```

### 7.2 테스트 및 드라이런 실행

```bash
# 단위 테스트
uv run pytest tests/crawlers/test_{site_name}.py -v

# 커버리지 확인
uv run pytest tests/crawlers/test_{site_name}.py \
    --cov=dereel/crawlers/{site_name} --cov-report=term-missing

# 드라이런 (알림 발송 없이 결과만 출력)
uv run python -m dereel.run \
    --type price \
    --site {site_name} \
    --dry-run \
    --log-level DEBUG
```

### 7.3 드라이런 통과 기준

```
✅ 통과 조건
    □ 오류 없이 실행 완료
    □ parse() 결과가 1개 이상의 Result 반환
    □ format_message() 결과가 의도한 포맷과 일치
    □ [DRY-RUN] 알림 발송 스킵 로그 출력

❌ 실패 시 재확인
    □ fetch()  → API 엔드포인트 / 파라미터 오타 확인
    □ parse()  → 실제 응답 구조와 키 이름 비교
    □ format_message() → PriceResult 필드 접근 오류
```

---

## 최종 체크리스트 (PR 전 확인)

```
□ dereel/crawlers/{site_name}.py 생성
□ fetch() / parse() / format_message() 구현 완료
□ parse()에서 KeyError 처리 및 _alert_structure_change() 연결
□ tests/crawlers/test_{site_name}.py 작성
□ 테스트 커버리지 80% 이상
□ 드라이런 통과
□ Telegram 실제 알림 수신 확인 (1회)
□ config/targets.yaml 섹션 추가 (enabled: true 전환)
□ FEATURES.md 업데이트
□ CRAWLING_STRATEGY.md 사이트별 전략 섹션 추가
□ CHANGELOG.md 기록
□ 커밋: feat(crawler): {사이트명} 크롤러 구현
```

---

## 참고 — 완성된 크롤러 예시

| 파일 | 방식 | 참고 포인트 |
|---|---|---|
| `apple_refurb.py` | JSON API | 가장 단순한 구조, 입문용 |
| `steam.py` | API + 순차 조회 | 복수 제품 + 딜레이 패턴 |
| `coupang.py` | API + HMAC 인증 | 서명 생성 로직 참고 |
| `amazon.py` | Playwright | 헤드리스 브라우저 패턴 |

---

## 변경 이력

| 버전 | 날짜 | 내용 | 작성자 |
|---|---|---|---|
| v0.1.0 | 2026-03-31 | 최초 초안 작성 | 한섭 |
