# DeReel — 데이터 명세서

> **버전:** v0.1.0
> **작성일:** 2026-03-31
> **작성자:** 한섭
> **연관 문서:** [ARCHITECTURE.md](./ARCHITECTURE.md) | [FEATURES.md](./FEATURES.md)

---

## 1. 데이터 구조 전체 개요

```
DeReel 데이터 계층
├── 런타임 모델 (Python Dataclass)
│   ├── StockResult          # 재고 크롤링 결과
│   └── PriceResult          # 가격 크롤링 결과
│
├── 상태 저장소 (Phase 1: JSON / Phase 2+: DynamoDB)
│   ├── stock_state.json     # 사이트별 이전 재고 스냅샷
│   ├── price_state.json     # 사이트별 이전 가격 스냅샷
│   └── alert_history.json   # 알림 발송 이력
│
└── 이력 저장소 (Phase 2+: DynamoDB + S3)
    ├── PriceHistory (raw)   # 크롤링 시점별 가격 원본 (1개월)
    ├── PriceMonthly         # 월별 집계 (1년)
    └── PriceYearly          # 연별 집계 (5년)
```

---

## 2. 런타임 데이터 모델

### 2.1 StockResult — 재고 결과

```python
# dereel/models/stock_result.py
from datetime import datetime
from pydantic import BaseModel, Field

class StockResult(BaseModel):
    site: str           # 사이트 식별자 (예: "apple_refurb")
    product_id: str     # 사이트 내 고유 식별자 (예: Apple SKU "MQTP3KH/A")
    name: str           # 제품명 (예: "AirPods Pro (2세대)")
    in_stock: bool      # 재고 여부 (True = 재고 있음)
    price: float        # 현재 가격 (현지 통화 기준)
    currency: str       # 원본 통화 코드 (예: "KRW")
    url: str            # 상품 페이지 URL
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

**유효성 검증 규칙**

| 필드 | 타입 | 필수 | 제약 조건 |
|---|---|---|---|
| `site` | str | ✅ | `apple_refurb` 고정 (Phase 1) |
| `product_id` | str | ✅ | 공백 불가, 사이트 내 유니크 |
| `name` | str | ✅ | 1자 이상 |
| `in_stock` | bool | ✅ | True / False |
| `price` | float | ✅ | 0 이상 (무료 제품은 0) |
| `currency` | str | ✅ | ISO 4217 코드 (KRW, USD, JPY …) |
| `url` | str | ✅ | `https://` 시작 |
| `fetched_at` | datetime | ✅ | UTC 기준 |

---

### 2.2 PriceResult — 가격 결과

```python
# dereel/models/price_result.py
from datetime import datetime
from pydantic import BaseModel, Field

class PriceResult(BaseModel):
    site: str               # 사이트 식별자 (예: "steam", "gog")
    product_id: str         # 사이트 내 고유 식별자
    name: str               # 제품명
    current_price: float    # 현재 가격 (현지 통화 기준)
    original_price: float   # 정가 (할인 전)
    currency: str           # 원본 통화 코드
    url: str                # 상품 페이지 URL
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_free(self) -> bool:
        return self.current_price == 0

    def should_notify(self, target_price: float) -> bool:
        """무료 전환 또는 목표가 이하 시 True"""
        if self.is_free:
            return True
        return self.current_price <= target_price
```

**사이트별 product_id 규칙**

| 사이트 | product_id 형식 | 예시 |
|---|---|---|
| `steam` (app) | Steam App ID (정수 문자열) | `"1245620"` |
| `steam` (package) | Steam Sub ID (정수 문자열) | `"6588"` |
| `steam` (bundle) | Steam Bundle ID (정수 문자열) | `"6588"` |
| `coupang` | 쿠팡 상품 ID | `"12345678"` |
| `gog` | GOG Product ID (정수 문자열) | `"1207658885"` |
| `epic` | Epic Offer ID (UUID) | `"a3b4c5d6-..."` |
| `amazon` | ASIN | `"B09V3KXJPB"` |

**복합 고유키 (composite key)**
```
{site}:{product_id}
예) steam:1245620
    coupang:12345678
    amazon:B09V3KXJPB
```

---

## 3. 상태 저장소 스키마 (Phase 1: JSON 파일)

Phase 1에서는 상태를 `data/` 디렉토리의 JSON 파일로 관리하며,  
크롤링 완료 후 GitHub repo에 커밋한다.

---

### 3.1 stock_state.json — 재고 스냅샷

```json
{
  "apple_refurb": {
    "last_updated": "2026-03-31T06:00:00Z",
    "products": {
      "MQTP3KH/A": {
        "name": "AirPods Pro (2세대)",
        "available": true,
        "price": 289000,
        "currency": "KRW",
        "url": "https://www.apple.com/kr/shop/product/MQTP3KH/A",
        "category": "airpods"
      },
      "MTJV3KH/A": {
        "name": "AirPods (4세대)",
        "available": false,
        "price": 189000,
        "currency": "KRW",
        "url": "https://www.apple.com/kr/shop/product/MTJV3KH/A",
        "category": "airpods"
      }
    }
  }
}
```

**스키마 정의**

| 경로 | 타입 | 설명 |
|---|---|---|
| `{site}` | object | 사이트별 루트 키 |
| `{site}.last_updated` | ISO 8601 string | 마지막 크롤링 시각 (UTC) |
| `{site}.products` | object | product_id를 키로 하는 제품 맵 |
| `{site}.products.{id}.name` | string | 제품명 |
| `{site}.products.{id}.available` | boolean | 재고 여부 |
| `{site}.products.{id}.price` | integer | 가격 (원화) |
| `{site}.products.{id}.currency` | string | 원본 통화 |
| `{site}.products.{id}.url` | string | 상품 URL |
| `{site}.products.{id}.category` | string | 카테고리 |

---

### 3.2 price_state.json — 가격 스냅샷

```json
{
  "steam": {
    "last_updated": "2026-03-31T06:00:00Z",
    "products": {
      "1245620": {
        "name": "Elden Ring",
        "price": 14950,
        "original_price": 59800,
        "discount_pct": 75.0,
        "currency": "KRW",
        "url": "https://store.steampowered.com/app/1245620",
        "is_free": false,
        "free_until": null
      }
    }
  },
  "coupang": {
    "last_updated": "2026-03-31T06:00:00Z",
    "products": {
      "12345678": {
        "name": "MacBook Air M3",
        "price": 1490000,
        "original_price": 1690000,
        "discount_pct": 11.8,
        "currency": "KRW",
        "url": "https://www.coupang.com/vp/products/12345678",
        "is_free": false,
        "free_until": null
      }
    }
  }
}
```

---

### 3.3 alert_history.json — 알림 발송 이력

```json
{
  "apple_refurb:MQTP3KH/A:stock": {
    "last_sent_at": "2026-03-31T06:12:00Z",
    "last_alerted_price": null,
    "send_count": 3
  },
  "steam:1245620:price": {
    "last_sent_at": "2026-03-30T09:00:00Z",
    "last_alerted_price": 15000,
    "send_count": 1
  }
}
```

**키 규칙**
```
{site}:{product_id}:{alert_type}

alert_type 값:
  stock  → 재고 입고 알림
  price  → 가격 하락 알림
  free   → 무료 배포 알림 (Epic)
  struct → 크롤링 구조 변경 경보
```

**스키마 정의**

| 필드 | 타입 | 설명 |
|---|---|---|
| `last_sent_at` | ISO 8601 string | 마지막 발송 시각 (UTC) |
| `last_alerted_price` | integer | null | 마지막 알림 발송 당시 가격 (재고 알림 등 해당 없으면 null) |
| `send_count` | integer | 누적 발송 횟수 |

**중복 방지 판단 로직**
```python
from datetime import datetime, timezone, timedelta

def can_send(alert_key: str, current_price: int | None = None) -> bool:
    record = alert_history.get(alert_key)
    if record is None:
        return True  # 최초 알림

    # 가격 하락 알림이고, 현재 가격이 마지막 알림 발송 당시 가격보다 낮다면 쿨다운 우회 발송
    if current_price is not None and record.get("last_alerted_price") is not None:
        if current_price < record["last_alerted_price"]:
            return True

    last_sent = datetime.fromisoformat(record["last_sent_at"])
    elapsed = datetime.now(timezone.utc) - last_sent
    return elapsed >= timedelta(hours=24)
```

---

## 4. 이력 저장소 스키마 (Phase 2+: DynamoDB)

Phase 2부터 가격 이력을 AWS DynamoDB에 저장한다.  
DynamoDB는 Partition Key + Sort Key 기반의 단일 테이블 설계를 채택한다.

### 4.1 테이블 설계 — 단일 테이블 패턴

```
테이블명: dereel-price-history

Partition Key (PK): site:product_id      예) "steam:1245620"
Sort Key (SK):      record_type#datetime  예) "raw#2026-03-31T06:00:00Z"
                                               "monthly#2026-03"
                                               "yearly#2026"
```

### 4.2 Raw 레코드 (1개월 이내 원본)

```json
{
  "PK": "steam:1245620",
  "SK": "raw#2026-03-31T06:00:00Z",
  "record_type": "raw",
  "name": "Elden Ring",
  "site": "steam",
  "product_id": "1245620",
  "price": 14950,
  "original_price": 59800,
  "discount_pct": 75.0,
  "currency": "KRW",
  "fetched_at": "2026-03-31T06:00:00Z",
  "ttl": 1751299200
}
```

> `ttl` 필드: DynamoDB TTL 기능으로 **30일 후 자동 삭제** (Unix timestamp)  
> 집계 완료 후 raw 데이터 삭제는 TTL이 처리

### 4.3 월별 집계 레코드 (1개월 초과 ~ 1년)

```json
{
  "PK": "steam:1245620",
  "SK": "monthly#2026-02",
  "record_type": "monthly",
  "name": "Elden Ring",
  "year_month": "2026-02",
  "min_price": 14950,
  "max_price": 59800,
  "avg_price": 42375.0,
  "record_count": 240,
  "currency": "KRW",
  "aggregated_at": "2026-03-01T00:00:00Z",
  "ttl": 1788364800
}
```

> `ttl`: **1년 후 자동 삭제** (연별 집계로 이전됨)

### 4.4 연별 집계 레코드 (1년 초과 ~ 5년)

```json
{
  "PK": "steam:1245620",
  "SK": "yearly#2025",
  "record_type": "yearly",
  "name": "Elden Ring",
  "year": "2025",
  "min_price": 11963,
  "max_price": 59800,
  "avg_price": 38540.0,
  "record_count": 2880,
  "currency": "KRW",
  "aggregated_at": "2026-01-01T00:00:00Z",
  "ttl": 1893456000
}
```

> `ttl`: **5년 후 자동 삭제**

### 4.5 DynamoDB 접근 패턴

| 쿼리 목적 | 접근 방식 | 예시 |
|---|---|---|
| 특정 제품 전체 이력 조회 | PK 조회 | `PK = "steam:1245620"` |
| 특정 제품 raw 이력 조회 | PK + SK begins_with | `SK begins_with "raw#"` |
| 특정 제품 월별 집계 조회 | PK + SK begins_with | `SK begins_with "monthly#"` |
| 특정 기간 이력 조회 | PK + SK between | `SK between "raw#2026-03-01" and "raw#2026-03-31"` |
| 최신 가격 조회 | PK + SK 내림차순 limit 1 | `SK begins_with "raw#"`, Limit=1, ScanIndexForward=False |

---

## 5. 집계 배치 스키마

### 5.1 집계 실행 규칙

```
월별 집계 배치:
  실행 시각: 매월 1일 00:30 KST (UTC 15:30 전월 말일)
  대상: SK begins_with "raw#", fetched_at < 30일 전
  출력: SK = "monthly#YYYY-MM" 레코드 생성
  정리: 집계 완료 후 raw TTL 30일로 단축 (즉시 삭제는 X)

연별 집계 배치:
  실행 시각: 매년 1월 1일 01:00 KST
  대상: SK begins_with "monthly#", year_month < 1년 전
  출력: SK = "yearly#YYYY" 레코드 생성
  정리: monthly TTL 1년으로 단축
```

### 5.2 집계 계산 명세

```python
from statistics import mean

def aggregate_monthly(records: list[dict]) -> dict:
    prices = [r["price"] for r in records]
    return {
        "min_price": min(prices),
        "max_price": max(prices),
        "avg_price": round(mean(prices), 1),
        "record_count": len(records),
    }

def aggregate_yearly(monthly_records: list[dict]) -> dict:
    """월별 집계에서 연별 집계 계산 (가중 평균)"""
    total_count = sum(r["record_count"] for r in monthly_records)
    weighted_sum = sum(r["avg_price"] * r["record_count"] for r in monthly_records)
    return {
        "min_price": min(r["min_price"] for r in monthly_records),
        "max_price": max(r["max_price"] for r in monthly_records),
        "avg_price": round(weighted_sum / total_count, 1),
        "record_count": total_count,
    }
```

> 연별 집계의 `avg_price`는 단순 평균이 아닌 **레코드 수 기반 가중 평균**을 사용한다.  
> (월별 레코드 수가 다를 수 있으므로)

---

## 6. 환경변수 및 설정 스키마

### 6.1 환경변수 목록

```bash
# .env.example (실제 값 미포함, repo에 커밋 가능)

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# 쿠팡 파트너스
COUPANG_ACCESS_KEY=your_access_key_here
COUPANG_SECRET_KEY=your_secret_key_here

# AWS (Phase 2+)
AWS_ACCESS_KEY_ID=your_aws_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_here
AWS_REGION=ap-northeast-2

# 설정 (선택, 기본값 있음)
DEREEL_LOG_LEVEL=INFO
DEREEL_DATA_DIR=./data
DEREEL_CONFIG_PATH=./config/targets.yaml
```

### 6.2 pydantic-settings 모델

```python
# dereel/core/settings.py
from pydantic_settings import BaseSettings
from pydantic import SecretStr

class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: SecretStr
    telegram_chat_id: str

    # 쿠팡 (선택)
    coupang_access_key: SecretStr | None = None
    coupang_secret_key: SecretStr | None = None

    # AWS (선택)
    aws_access_key_id: SecretStr | None = None
    aws_secret_access_key: SecretStr | None = None
    aws_region: str = "ap-northeast-2"

    # 앱 설정
    log_level: str = "INFO"
    data_dir: str = "./data"
    config_path: str = "./config/targets.yaml"

    class Config:
        env_prefix = "DEREEL_"
        env_file = ".env"

settings = Settings()
```

---

## 7. targets.yaml 전체 스키마

루트 키는 `targets` (리스트 형식). 각 항목은 `site`, `type`, `interval_hours` 필수.

```yaml
# config/targets.yaml
targets:

  # ── Apple 리퍼비시 (stock) ────────────────────────
  - site: apple_refurb
    type: stock
    interval_hours: 4
    url: "https://www.apple.com/kr/shop/refurbished/airpods"
    enabled: true
    dry_run: false

  # ── Steam (price) ─────────────────────────────────
  - site: steam
    type: price
    interval_hours: 3
    currency: KRW
    enabled: true
    dry_run: false
    products:
      - app_id: "1245620"         # Steam App ID
        name: "Elden Ring"
        target_price: 15000
      - package_id: "123"         # Steam Sub(Package) ID
        name: "Some Collection"
        target_price: 10000
      - bundle_id: "6588"         # Steam Bundle ID
        name: "Monkey Island Collection"
        target_price: 20000

  # ── GOG (price) ───────────────────────────────────
  - site: gog
    type: price
    interval_hours: 6
    currency: USD
    enabled: true
    dry_run: false
    products:
      - product_id: "1207658885"
        name: "The Witcher 3: Wild Hunt"
        target_price: 4.99

  # ── Epic (price, 미구현) ───────────────────────────
  - site: epic
    type: price
    interval_hours: 6
    currency: KRW
    enabled: false
    dry_run: true
    products: []

  # ── Amazon (price, 미구현) ─────────────────────────
  - site: amazon
    type: price
    interval_hours: 12
    currency: KRW
    enabled: false
    dry_run: true
    products: []
```

**필드 정의**

| 필드 | 타입 | 기본값 | 제약 |
|---|---|---|---|
| `site` | string | — | CRAWLER_REGISTRY 등록 키와 일치 |
| `type` | string | `"stock"` | `stock` 또는 `price` |
| `enabled` | boolean | `true` | false면 완전 스킵 |
| `interval_hours` | number | `1` | 1 이상 24 이하 |
| `currency` | string | `"USD"` | ISO 4217 코드 |
| `dry_run` | boolean | `false` | true면 알림 미발송 |
| `url` | string | — | stock 타입 필수 |
| `products[].target_price` | number | `0` | 현지 통화 기준 목표가 |

**Steam products 식별자 우선순위**

하나의 product 항목에는 `app_id`, `package_id`, `bundle_id` 중 하나만 사용:

| 필드 | 대응 API | 스토어 URL |
|---|---|---|
| `app_id` | `/api/appdetails` | `/app/{id}` |
| `package_id` | `/api/packagedetails` | `/sub/{id}` |
| `bundle_id` | `/api/bundledetails` | `/bundle/{id}` |

---

## 8. 변경 이력

| 버전 | 날짜 | 내용 | 작성자 |
|---|---|---|---|
| v0.1.0 | 2026-03-31 | 최초 초안 작성 | 한섭 |
| v0.2.0 | 2026-05-28 | StockResult/PriceResult Pydantic 모델로 교체, targets.yaml 실제 구조 반영, Steam bundle_id 추가 | 한섭 |

