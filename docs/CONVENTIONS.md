# DeReel — 코드 컨벤션 및 개발 규칙

> **버전:** v0.1.0
> **작성일:** 2026-03-31
> **작성자:** 한섭
> **연관 문서:** [DEV_SETUP.md](./DEV_SETUP.md) | [HOW_TO_ADD_CRAWLER.md](./HOW_TO_ADD_CRAWLER.md)

---

## 1. 전체 원칙

| 원칙 | 설명 |
|---|---|
| **명시적 > 암묵적** | 코드만 봐도 의도가 명확해야 한다 |
| **단순함 우선** | 기발한 코드보다 읽기 쉬운 코드 |
| **일관성** | 팀 규칙이 개인 취향보다 우선 |
| **작게 커밋** | 하나의 커밋은 하나의 목적만 |

---

## 2. Python 코드 스타일

### 2.1 기본 규칙

| 항목 | 규칙 |
|---|---|
| 포맷터 | `black` (라인 길이 100) |
| 린터 | `ruff` |
| 타입 힌트 | 모든 함수 시그니처에 필수 |
| 독스트링 | 핵심 모듈 함수에 작성 |
| 최대 함수 길이 | 50줄 이하 권장 |
| 최대 파일 길이 | 300줄 이하 권장 |

### 2.2 네이밍 컨벤션

```python
# 변수 / 함수: snake_case
product_id = "MQTP3KH/A"
def fetch_price(app_id: int) -> dict: ...

# 클래스: PascalCase
class AppleRefurbCrawler(BaseCrawler): ...

# 상수: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
DEFAULT_COOLDOWN_HOURS = 24

# 비공개 멤버: 언더스코어 접두사
def _parse_raw(self, data: dict) -> list[dict]: ...

# 타입 별칭: PascalCase
ProductMap = dict[str, StockResult]
```

### 2.3 타입 힌트

```python
# ✅ Good — 모든 파라미터와 반환값에 타입 명시
async def fetch(self, category: str) -> dict[str, Any]:
    ...

# ✅ Good — Optional 대신 X | None 사용 (Python 3.10+)
def get_last_alert(key: str) -> datetime | None:
    ...

# ✅ Good — list, dict 소문자 사용 (Python 3.9+)
def parse(self, items: list[dict]) -> list[StockResult]:
    ...

# ❌ Bad — 타입 힌트 없음
def fetch(self, category):
    ...

# ❌ Bad — 구형 Optional 문법
from typing import Optional
def get_last_alert(key: str) -> Optional[datetime]:
    ...
```

### 2.4 임포트 순서

`ruff`가 자동 정렬하지만, 원칙은 아래와 같다.

```python
# 1. 표준 라이브러리
import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path

# 2. 서드파티 라이브러리
import httpx
from pydantic import BaseModel

# 3. 내부 모듈 (dereel.*)
from dereel.core.settings import settings
from dereel.models.stock_result import StockResult
```

### 2.5 예외 처리

```python
# ✅ Good — 구체적인 예외 타입 명시
try:
    response = await client.get(url)
    response.raise_for_status()
except httpx.TimeoutException:
    logger.warning(f"{self.site_name} | 타임아웃 발생")
except httpx.HTTPStatusError as e:
    logger.error(f"{self.site_name} | HTTP 오류: {e.response.status_code}")

# ❌ Bad — 모든 예외를 하나로 묶기
try:
    ...
except Exception:
    pass  # 절대 금지
```

### 2.6 매직 넘버 금지

```python
# ✅ Good — 상수로 이름 부여
MAX_RETRY = 1
TIMEOUT_SECONDS = 30
MIN_DELAY = 3.0
MAX_DELAY = 8.0

await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

# ❌ Bad — 숫자가 의미 불명
await asyncio.sleep(random.uniform(3.0, 8.0))
```

### 2.7 f-string 사용

```python
# ✅ Good
logger.info(f"{self.site_name} | 크롤링 완료 ({len(results)}개)")

# ❌ Bad — % 포맷팅 (구형)
logger.info("%s | 크롤링 완료 (%d개)" % (self.site_name, len(results)))

# ❌ Bad — .format() (불필요하게 장황)
logger.info("{} | 완료".format(self.site_name))
```

---

## 3. 로깅 컨벤션

### 3.1 loguru 사용

```python
from loguru import logger

# 모듈 최상단에서 컨텍스트 바인딩
log = logger.bind(site="apple_refurb")

# 이후 사용
log.info("크롤링 시작")
log.warning("재시도 발생")
log.error("파싱 실패")
```

### 3.2 로그 메시지 포맷 규칙

```python
# 형식: "{site_name} | {동작} ({상세})"
logger.info(f"{self.site_name} | 크롤링 완료 (3개 제품 감지)")
logger.info(f"{self.site_name} | 알림 발송 성공 (AirPods Pro 2세대)")
logger.warning(f"{self.site_name} | 알림 스킵 - 24시간 내 중복 (AirPods 4세대)")
logger.error(f"{self.site_name} | HTTP 429 - 다음 주기에 재시도")
logger.error(f"{self.site_name} | 파싱 실패 - 구조 변경 의심: {e}")
```

### 3.3 레벨별 사용 기준

| 레벨 | 사용 기준 | 예시 |
|---|---|---|
| `DEBUG` | HTTP 요청/응답 원본 (로컬 개발만) | 응답 JSON 덤프 |
| `INFO` | 정상 처리 흐름 | 크롤링 완료, 알림 발송 성공 |
| `WARNING` | 처리됐지만 주의 필요 | 재시도, 알림 중복 스킵 |
| `ERROR` | 처리 실패 (시스템은 계속 동작) | 크롤링 실패, 발송 실패 |
| `CRITICAL` | 시스템 중단 수준 오류 | 설정 파일 없음, 인증 오류 |

### 3.4 민감 정보 마스킹

```python
# ✅ Good — 토큰 마스킹
token = settings.telegram_bot_token.get_secret_value()
masked = f"{token[:6]}...{token[-4:]}"
logger.debug(f"Bot Token: {masked}")   # 7xxxxxx...xKJpB

# ❌ Bad — 원본 그대로 로깅
logger.debug(f"Bot Token: {token}")
```

---

## 4. Git 컨벤션

### 4.1 브랜치 전략

```
main              ← 항상 동작 가능한 상태 유지
└── feat/...      ← 새 기능 개발
└── fix/...       ← 버그 수정
└── chore/...     ← 설정, 문서, 의존성 업데이트
└── refactor/...  ← 기능 변경 없는 코드 개선
```

**브랜치 명명 규칙**
```bash
feat/steam-price-crawler
fix/apple-refurb-parsing-error
chore/update-dependencies
docs/add-runbook
```

### 4.2 커밋 메시지 컨벤션

[Conventional Commits](https://www.conventionalcommits.org/) 형식을 따른다.

```
{type}({scope}): {subject}

[optional body]
[optional footer]
```

**type 목록**

| type | 사용 상황 |
|---|---|
| `feat` | 새 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 수정 |
| `chore` | 빌드, 설정, 의존성 변경 |
| `refactor` | 기능 변경 없는 코드 개선 |
| `test` | 테스트 추가 및 수정 |
| `style` | 포맷팅 (기능 변경 없음) |
| `perf` | 성능 개선 |

**실제 예시**
```bash
# ✅ Good
feat(crawler): Apple 리퍼비시 크롤러 구현
fix(notifier): Telegram 발송 타임아웃 오류 수정
docs(arch): Phase 2 DynamoDB 설계 추가
chore(deps): httpx 0.27.0으로 업그레이드
test(comparator): 재고 변동 감지 엣지 케이스 테스트 추가

# ❌ Bad
update code
fix bug
작업중
```

**GitHub Actions 커밋 메시지**
```bash
# 자동 커밋은 반드시 [skip ci] 포함 (무한 루프 방지)
chore: update stock state [skip ci]
chore: update price state [skip ci]
```

### 4.3 커밋 단위 원칙

```
# ✅ Good — 하나의 커밋 = 하나의 목적
feat(crawler): Steam 가격 크롤러 fetch() 구현
feat(crawler): Steam 가격 크롤러 parse() 구현
test(crawler): Steam 크롤러 단위 테스트 추가

# ❌ Bad — 한 커밋에 너무 많은 변경
feat: 스팀, 쿠팡, GOG 크롤러 전부 추가하고 버그도 수정함
```

### 4.4 PR(Pull Request) 규칙

- 제목: 커밋 메시지와 동일 형식 (`feat(crawler): ...`)
- 본문: 변경 이유, 변경 내용, 테스트 방법
- `main` 직접 Push 금지 (본인 단독 프로젝트이더라도 PR 습관화)
- Merge 전 `uv run pytest` 통과 확인

---

## 5. 파일 및 디렉토리 네이밍

```
dereel/
├── crawlers/
│   ├── apple_refurb.py     # snake_case, 사이트명 그대로
│   ├── steam.py
│   └── coupang.py
├── core/
│   ├── base_crawler.py     # 역할을 명확히
│   ├── alert_evaluator.py
│   └── message_formatter.py
├── models/
│   ├── stock_result.py     # 모델명_result.py 형식
│   └── price_result.py
└── tests/
    ├── test_comparator.py  # test_{모듈명}.py
    └── crawlers/
        └── test_apple_refurb.py
```

**규칙 요약**
- 모든 파일명: `snake_case.py`
- 테스트 파일: `test_` 접두사 필수 (pytest 자동 인식)
- 크롤러 파일: 사이트 식별자와 동일하게 (`targets.yaml`의 키와 일치)

---

## 6. 테스트 컨벤션

### 6.1 테스트 구조

```python
# tests/test_comparator.py

import pytest
from dereel.core.comparator import should_alert_stock
from dereel.models.stock_result import StockResult


class TestShouldAlertStock:
    """재고 입고 알림 조건 판단 테스트"""

    def test_입고_감지_정상(self):
        """이전 품절 → 현재 재고 있음: 알림 발송"""
        previous = make_stock(available=False)
        current = make_stock(available=True)
        assert should_alert_stock(current, previous) is True

    def test_최초_실행_알림_없음(self):
        """이전 상태 없음: 최초 실행이므로 알림 없음"""
        current = make_stock(available=True)
        assert should_alert_stock(current, None) is False

    def test_재고_유지_알림_없음(self):
        """이전에도 재고 있음 → 변동 없음: 알림 없음"""
        previous = make_stock(available=True)
        current = make_stock(available=True)
        assert should_alert_stock(current, previous) is False

    def test_품절_전환_알림_없음(self):
        """재고 있음 → 품절: 입고 알림 아님"""
        previous = make_stock(available=True)
        current = make_stock(available=False)
        assert should_alert_stock(current, previous) is False
```

### 6.2 테스트 명명 규칙

```python
# 메서드명: test_{상황}_{기대결과} 또는 한국어 자유 서술
def test_입고_감지_정상():         # ✅ 한국어 서술 (권장)
def test_stock_detected_alert():   # ✅ 영어 snake_case
def test1():                       # ❌ 의미 없는 이름
```

### 6.3 픽스처(Fixture) 사용

```python
# conftest.py
import pytest
from dereel.models.stock_result import StockResult
from datetime import datetime, timezone

@pytest.fixture
def base_stock() -> StockResult:
    return StockResult(
        site="apple_refurb",
        product_id="MQTP3KH/A",
        name="AirPods Pro (2세대)",
        available=True,
        price=289000,
        currency="KRW",
        url="https://www.apple.com/kr/shop/product/MQTP3KH/A",
        fetched_at=datetime.now(timezone.utc),
    )

# 테스트에서 사용
def test_알림_조건(base_stock):
    base_stock.available = False
    ...
```

### 6.4 HTTP 모킹

```python
# httpx 요청 모킹 (respx 사용)
import respx
import httpx

@respx.mock
async def test_fetch_apple_refurb():
    respx.get("https://www.apple.com/kr/shop/product-locator-meta").mock(
        return_value=httpx.Response(200, json={"tiles": [...]})
    )
    crawler = AppleRefurbCrawler(config={})
    result = await crawler.fetch("airpods")
    assert len(result["tiles"]) > 0
```

---

## 7. 설정 파일 컨벤션

### 7.1 targets.yaml 수정 규칙

- `enabled: false` 가 기본값 — 명시적으로 `true`로 바꿔야 활성화
- 새 제품 추가 시 기존 항목 아래에 추가 (알파벳순 정렬 불필요)
- 제품명(`name`)은 한국어 또는 공식 영문명 사용 (임의 약칭 금지)
- 커밋 메시지: `chore(config): 감시 제품 추가 - {제품명}`

### 7.2 .env 규칙

- `.env`는 절대 커밋 금지 (`.gitignore` 등록 확인)
- `.env.example`은 실제 값 없이 항상 최신 상태 유지
- 새 환경변수 추가 시 `.env.example`과 `DEV_SETUP.md` 동시 업데이트

---

## 8. 문서 컨벤션

### 8.1 문서 업데이트 규칙

| 변경 종류 | 함께 업데이트할 문서 |
|---|---|
| 새 크롤러 추가 | `FEATURES.md`, `CRAWLING_STRATEGY.md`, `HOW_TO_ADD_CRAWLER.md`, `CHANGELOG.md` |
| 알림 메시지 변경 | `NOTIFICATION_SPEC.md`, `CHANGELOG.md` |
| 데이터 모델 변경 | `DATA_SCHEMA.md`, `CHANGELOG.md` |
| 새 환경변수 추가 | `DEV_SETUP.md`, `.env.example` |
| 워크플로 변경 | `DEPLOYMENT.md`, `ARCHITECTURE.md` |

### 8.2 CHANGELOG.md 작성 형식

[Keep a Changelog](https://keepachangelog.com/) 형식을 따른다.

```markdown
## [Unreleased]

### Added
- Steam 가격 크롤러 구현 (#12)

### Fixed
- Apple 리퍼비시 파싱 오류 수정 (#15)

## [0.2.0] - 2026-04-30

### Added
- GOG, Epic Games 가격 크롤러 구현
- 할인율 알림 기능 추가
```

---

## 9. 변경 이력

| 버전 | 날짜 | 내용 | 작성자 |
|---|---|---|---|
| v0.1.0 | 2026-03-31 | 최초 초안 작성 | 한섭 |

