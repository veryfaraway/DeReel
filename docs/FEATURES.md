# DeReel — 기능 명세서

> **버전:** v0.1.0  
> **작성일:** 2026-03-24  
> **작성자:** 한섭  
> **연관 문서:** [PRD.md](./PRD.md)

---

## 1. 기능 우선순위 기준

| 우선순위 | 정의 | 비고 |
|---|---|---|
| **P0** | MVP 필수 — 없으면 서비스 불가 | Phase 1-A 완료 기준 |
| **P1** | 중요 기능 — 다음 스프린트 허용 | Phase 1-B ~ 2 대상 |
| **P2** | Nice to have — 여유 시 구현 | Phase 3 이후 |

---

## 2. 기능 목록 전체 개요

| ID | 기능명 | 분류 | 우선순위 | Phase |
|---|---|---|---|---|
| F-01 | Apple 리퍼비시 재고 크롤링 | 크롤링 | P0 | 1-A |
| F-02 | 재고 변동 감지 (신규 입고) | 감지 | P0 | 1-A |
| F-03 | Telegram 알림 발송 | 알림 | P0 | 1-A |
| F-04 | 알림 중복 방지 (1일 1회) | 알림 | P0 | 1-A |
| F-05 | targets.yaml 감시 목록 관리 | 설정 | P0 | 1-A |
| F-06 | GitHub Actions 크론 스케줄링 | 운영 | P0 | 1-A |
| F-07 | Apple 리퍼비시 전체 제품군 확대 | 크롤링 | P1 | 1-B |
| F-08 | Steam 가격 크롤링 | 크롤링 | P1 | 2-A |
| F-09 | 쿠팡 가격 크롤링 | 크롤링 | P1 | 2-A |
| F-10 | GOG 가격 크롤링 | 크롤링 | P1 | 2-A |
| F-11 | Epic Games 가격/무료 게임 크롤링 | 크롤링 | P1 | 2-A |
| F-12 | Amazon 가격 크롤링 | 크롤링 | P1 | 2-A |
| F-13 | 목표가 기반 가격 알림 | 알림 | P1 | 2-A |
| F-14 | 가격 이력 저장 및 집계 | 데이터 | P1 | 2-A |
| F-15 | Grafana 대시보드 | 대시보드 | P1 | 2-B |
| F-16 | 웹 UI 감시 목록 관리 | 대시보드 | P1 | 2-B |
| F-17 | Slack 알림 채널 추가 | 알림 | P2 | 2-B |
| F-18 | 가격 X% 이상 하락 알림 | 알림 | P2 | 2-B |

---

## 3. 기능 상세 명세

---

### F-01 | Apple 리퍼비시 재고 크롤링

| 항목 | 내용 |
|---|---|
| **우선순위** | P0 |
| **Phase** | 1-A |
| **크롤링 방식** | 비공개 JSON API (HTML 파싱 불필요) |
| **엔드포인트** | `https://www.apple.com/kr/shop/product-locator-meta?family=airpods` |
| **인증** | 불필요 (공개 엔드포인트) |
| **기본 주기** | 4시간 (설정 파일로 변경 가능) |

**요청 규칙**
- `User-Agent`: 실제 브라우저 문자열 사용 필수
- 요청 간격: 크롤링 주기 내에서 단발성 요청 (반복 루프 금지)
- `robots.txt` 준수 여부 매 실행 시 확인

**응답 파싱 대상 필드**
```json
{
  "partNumber": "제품 고유 번호 (SKU)",
  "name": "제품명",
  "price": { "currentPrice": 숫자 },
  "isSoldOut": true/false,
  "productUrl": "스토어 상품 링크"
}
```

**엣지 케이스**
- API 응답 구조 변경 시: 파싱 실패 에러 로그 기록 후 다음 주기 재시도
- 네트워크 타임아웃: 30초 초과 시 재시도 1회 후 실패 처리
- HTTP 429 (Rate Limit): 60분 대기 후 재시도

---

### F-02 | 재고 변동 감지 (신규 입고)

| 항목 | 내용 |
|---|---|
| **우선순위** | P0 |
| **Phase** | 1-A |
| **감지 기준** | 이전 크롤링 결과 대비 `isSoldOut: false` 로 변경된 제품 |

**감지 로직**
```
이전_재고 = storage.load(site="apple_refurb")   # Set[partNumber]
현재_재고 = crawler.fetch()                      # Set[partNumber]

신규_입고 = 현재_재고 - 이전_재고
# 이전에 없던 SKU가 새로 등장 = 신규 입고

storage.save(site="apple_refurb", data=현재_재고)
```

**엣지 케이스**
- 최초 실행 시 이전 데이터 없음: 현재 재고를 저장만 하고 알림 미발송
- 크롤링 실패로 현재 데이터가 비어있을 경우: 비교 로직 스킵 (오탐 방지)

---

### F-03 | Telegram 알림 발송

| 항목 | 내용 |
|---|---|
| **우선순위** | P0 |
| **Phase** | 1-A |
| **라이브러리** | `python-telegram-bot` |
| **설정값** | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (GitHub Secrets) |

**재고 알림 메시지 포맷**
```
🍎 [Apple 리퍼비시 입고 알림]

📦 제품명: AirPods Pro (2세대)
💰 가격: ₩289,000
🔗 링크: https://www.apple.com/kr/shop/...
🕐 감지 시각: 2026-03-24 09:30 KST
```

**가격 알림 메시지 포맷**
```
💸 [가격 하락 알림] Steam

🎮 제품명: Elden Ring
💰 현재 가격: ₩29,800 (목표가: ₩30,000)
📉 할인율: 75% OFF
🔗 링크: https://store.steampowered.com/...
🕐 감지 시각: 2026-03-24 12:00 KST
```

**엣지 케이스**
- Telegram API 오류 시: 에러 로그 기록, 알림 미발송으로 처리 (재시도 없음)
- 메시지 길이 초과 (4096자): 제품명·가격·링크만 포함한 축약 메시지로 대체

---

### F-04 | 알림 중복 방지 (1일 1회)

| 항목 | 내용 |
|---|---|
| **우선순위** | P0 |
| **Phase** | 1-A |
| **기준** | 동일 제품(SKU/product_id) + 동일 알림 유형(재고/가격) 기준 24시간 |

**중복 판단 로직**
```
알림_키 = f"{site}:{product_id}:{alert_type}"
마지막_발송시각 = alert_history.get(알림_키)

if 마지막_발송시각 is None or (현재시각 - 마지막_발송시각) >= 24시간:
    notifier.send(message)
    alert_history.save(알림_키, 현재시각)
else:
    # 24시간 미경과 → 발송 스킵, 로그만 기록
```

**엣지 케이스**
- 입고 → 품절 → 재입고가 24시간 내 반복: 최초 입고 알림 1회만 발송
- 알림 이력 저장소 접근 실패 시: 안전하게 발송 스킵 (중복 발송보다 미발송 우선)

---

### F-05 | targets.yaml 감시 목록 관리

| 항목 | 내용 |
|---|---|
| **우선순위** | P0 |
| **Phase** | 1-A |
| **파일 위치** | `config/targets.yaml` |

**파일 구조 명세**
```yaml
crawlers:
  apple_refurb:
    enabled: true
    interval_hours: 4          # 크롤링 주기 (시간)
    region: kr                 # 국가 코드
    categories:                # 감시할 카테고리 목록
      - airpods
      # - mac
      # - iphone
    products:                  # 특정 제품만 감시 시 SKU 지정 (비워두면 카테고리 전체)
      - partNumber: "MQTP3KH/A"
        name: "AirPods Pro (2세대)"

  steam:
    enabled: false             # Phase 2-A 활성화
    interval_hours: 3
    products:
      - app_id: 1245620
        name: "Elden Ring"
        target_price: 30000    # 원화 기준 목표가

  coupang:
    enabled: false
    interval_hours: 3
    products:
      - product_id: "12345678"
        name: "MacBook Air M3"
        target_price: 1500000

notifications:
  telegram:
    enabled: true
    # BOT_TOKEN, CHAT_ID는 GitHub Secrets에서 주입
```

**유효성 검사 규칙**
- `interval_hours`: 최솟값 1, 최댓값 24
- `target_price`: 0 이상 정수
- `enabled: false` 인 크롤러는 실행 목록에서 제외

---

### F-06 | GitHub Actions 크론 스케줄링

| 항목 | 내용 |
|---|---|
| **우선순위** | P0 |
| **Phase** | 1-A |
| **워크플로 파일** | `.github/workflows/crawl_stock.yml`, `.github/workflows/crawl_price.yml` |

**워크플로 분리 기준**

| 워크플로 | 대상 크롤러 | 기본 주기 |
|---|---|---|
| `crawl_stock.yml` | Apple 리퍼비시 | 4시간 (`0 */4 * * *`) |
| `crawl_price.yml` | Steam, 쿠팡, GOG, Epic, Amazon | 3시간 (`0 */3 * * *`) |

**워크플로 구성 요소**
```yaml
# crawl_stock.yml 예시
name: Crawl Stock
on:
  schedule:
    - cron: '0 */4 * * *'
  workflow_dispatch:           # 수동 실행 지원

jobs:
  crawl:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python -m dereel.run --type stock
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
```

**엣지 케이스**
- GitHub Actions cron 지연 (최대 수 분): 허용 범위로 간주
- 워크플로 실행 실패 시: GitHub 이메일 알림으로 인지 (별도 장애 알림 미구현, Phase 1)

---

### F-07 | Apple 리퍼비시 전체 제품군 확대

| 항목 | 내용 |
|---|---|
| **우선순위** | P1 |
| **Phase** | 1-B |
| **추가 카테고리** | mac, iphone, ipad, applewatch, accessories |

`targets.yaml`의 `categories` 항목에 카테고리 추가만으로 확장 가능하도록 F-01 구현 시 카테고리 루프 구조 설계 필수.

---

### F-08 ~ F-12 | 가격 크롤링 (Steam / 쿠팡 / GOG / Epic / Amazon)

| ID | 사이트 | 방식 | 인증 | 비고 |
|---|---|---|---|---|
| F-08 | Steam | 공식 Store API | 불필요 | `appdetails?appids=` |
| F-09 | 쿠팡 | 파트너스 API | Access/Secret Key | `developers.coupangcorp.com` |
| F-10 | GOG | 비공식 API + HTML | 불필요 | `api.gog.com/products/{id}` |
| F-11 | Epic Games | HTML 파싱 | 불필요 | 무료 게임 감지 포함 |
| F-12 | Amazon | HTML 파싱 | 불필요 | Playwright 헤드리스 필요 |

**공통 응답 정규화 포맷** (사이트 무관하게 동일 구조로 변환)
```python
@dataclass
class PriceResult:
    site: str           # "steam" | "coupang" | "gog" | "epic" | "amazon"
    product_id: str     # 사이트별 고유 ID
    name: str           # 제품명
    price: int          # 현재 가격 (원화 기준, 환율 변환 포함)
    currency: str       # 원본 통화 코드 ("KRW", "USD" 등)
    original_price: int # 정가 (할인 전)
    discount_pct: float # 할인율 (0.0 ~ 100.0)
    url: str            # 구매 링크
    fetched_at: str     # ISO 8601 타임스탬프
```

---

### F-13 | 목표가 기반 가격 알림

| 항목 | 내용 |
|---|---|
| **우선순위** | P1 |
| **Phase** | 2-A |
| **알림 조건** | `현재 가격 <= target_price` |
| **중복 방지** | F-04와 동일 규칙 적용 (24시간 1회) |

---

### F-14 | 가격 이력 저장 및 집계

| 항목 | 내용 |
|---|---|
| **우선순위** | P1 |
| **Phase** | 2-A |
| **저장소** | AWS DynamoDB 또는 S3 + Parquet (OQ-4 결정 후 확정) |
| **최대 보관 기간** | 5년 |

**보관 정책 상세**

| 데이터 나이 | 보관 방식 | 집계 스케줄 |
|---|---|---|
| 0 ~ 1개월 | raw 원본 전체 저장 | — |
| 1개월 초과 ~ 1년 | 월별 집계 (min/max/avg) | 매월 1일 00:00 KST |
| 1년 초과 ~ 5년 | 연별 집계 (min/max/avg) | 매년 1월 1일 00:00 KST |
| 5년 초과 | 자동 삭제 | 연간 집계 시 동시 처리 |

**저장 데이터 구조**
```python
# Raw 레코드
{
  "pk": "steam:1245620",       # site:product_id
  "sk": "2026-03-24T09:30:00", # 수집 시각 (정렬 키)
  "price": 29800,
  "currency": "KRW",
  "discount_pct": 75.0
}

# 월별 집계 레코드
{
  "pk": "steam:1245620",
  "sk": "2026-03",             # YYYY-MM
  "min_price": 14900,
  "max_price": 59800,
  "avg_price": 42350.0,
  "record_count": 240          # 집계된 원본 레코드 수
}
```

---

### F-15 | Grafana 대시보드

| 항목 | 내용 |
|---|---|
| **우선순위** | P1 |
| **Phase** | 2-B |
| **구현 방식** | Grafana OSS (Docker 또는 AWS Lightsail) |
| **데이터 소스** | DynamoDB Plugin 또는 S3 + Athena |

**제공할 패널 목록**
- 제품별 가격 트렌드 (시계열 라인 차트)
- 최저가 달성 횟수 히스토그램
- 재고 입고 타임라인
- 사이트별 크롤링 성공/실패율

---

### F-16 | 웹 UI 감시 목록 관리

| 항목 | 내용 |
|---|---|
| **우선순위** | P1 |
| **Phase** | 2-B |
| **구현 방식** | targets.yaml CRUD API + Grafana 연동 또는 별도 Vue.js UI |

**기능 목록**
- 감시 제품 추가/수정/삭제
- 크롤러 활성화/비활성화 토글
- 목표가 변경
- 알림 이력 조회

---

### F-17 | Slack 알림 채널 추가

| 항목 | 내용 |
|---|---|
| **우선순위** | P2 |
| **Phase** | 2-B |
| **구현 방식** | Slack Incoming Webhook |

F-03의 Notifier 클래스에 Slack 어댑터 추가. 제품별로 `notification_channel: telegram | slack | both` 설정 가능하도록 확장.

---

### F-18 | 가격 X% 이상 하락 알림

| 항목 | 내용 |
|---|---|
| **우선순위** | P2 |
| **Phase** | 2-B |
| **알림 조건** | `(이전가격 - 현재가격) / 이전가격 * 100 >= alert_threshold` |

`targets.yaml`에 `alert_threshold: 30` 형태로 설정. 목표가 조건(F-13)과 OR 조건으로 동작.

---

## 4. 기능 간 의존 관계

```
F-05 (targets.yaml)
  └─→ F-01 (Apple 크롤링)
        └─→ F-02 (재고 감지)
              └─→ F-03 (Telegram 알림)
                    └─→ F-04 (중복 방지)

F-06 (GitHub Actions)
  └─→ F-01, F-08 ~ F-12 (모든 크롤러 실행)

F-08 ~ F-12 (가격 크롤링)
  └─→ F-13 (목표가 알림)
  └─→ F-14 (가격 이력 저장)
        └─→ F-15 (Grafana 대시보드)
        └─→ F-16 (웹 UI)
```

---

## 5. 변경 이력

| 버전 | 날짜 | 내용 | 작성자 |
|---|---|---|---|
| v0.1.0 | 2026-03-24 | 최초 초안 작성 | 한섭 |

