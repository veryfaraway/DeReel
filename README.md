# DeReel

> **Data Extraction & REEL Engine**  
> 크롤링 기반 재고·가격 감시 및 Telegram 알림 시스템

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Cron-2088FF?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/features/actions)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](./LICENSE)

---

## 어떤 프로젝트인가요?

원하는 제품이 입고되거나, 목표 가격 이하로 내려가거나, 게임이 무료 배포되는 순간  
**Telegram으로 즉시 알림**을 받는 개인용 감시 봇입니다.

```text
🍎 [Apple 리퍼비시 입고]

📦 리퍼비쉬 iPad Pro 11(M4) Wi-Fi 256GB - 스페이스 블랙
💰 가격: ₩1,029,000
🔗 https://www.apple.com/kr/shop/product/FVV83KH/A
```

```text
🎮 [Steam 가격 알림]

🕹 Elden Ring
💸 현재가: ₩33,000 (50% 할인)
📌 원가:   ₩66,000
🎯 목표가: ₩33,000
🔗 https://store.steampowered.com/app/1245620
```

서버 없이 **GitHub Actions만으로 동작**하기 때문에 운영 비용이 $0입니다.

---

## 주요 기능

| 기능 | 설명 | 상태 |
|---|---|---|
| 🍎 Apple 리퍼비시 재고 감시 | 입고 즉시 Telegram 알림 | ✅ Phase 1-A |
| 💸 Steam 가격 감시 | 앱 / 패키지 / 번들 목표가 도달 시 알림 | ✅ Phase 1-B |
| 🎮 GOG 가격 감시 | 목표가 도달 시 알림 | ✅ Phase 1-B |
| 🎁 Epic 무료 게임 알림 | 무료 배포 시작 즉시 알림 (watchlist 지원) | ✅ Phase 1-B |
| 🛒 쿠팡 가격 감시 | 파트너스 공식 API 사용 | ⬜ Phase 2-A |
| 📦 Amazon 가격 감시 | Playwright 헤드리스 브라우저 | ⬜ Phase 2-A |
| 📊 가격 트렌드 대시보드 | Grafana 기반 가격 이력 시각화 | ⬜ Phase 2-B |

---

## 아키텍처

```text
⏰ GitHub Actions (crawl.yml — 매시간 실행)
        │
        ▼
🐍 run.py [--config <file>]
   config/*.yaml 자동 탐색, interval_hours로 사이트별 실행 주기 제어
        │
        ├── config/stock.yaml    → apple_refurb
        ├── config/games.yaml    → steam / gog / epic
        └── config/shopping.yaml → amazon / coupang (예정)
        │
        ▼
🕷️  Crawlers
  ├── apple_refurb.py   Playwright + Bootstrap JSON 파싱
  ├── steam.py          Store API (app / package / bundle)
  ├── gog.py            비공식 REST API
  ├── epic.py           무료 프로모션 API (watchlist 필터링 지원)
  ├── coupang.py        파트너스 API                          [예정]
  └── amazon.py         Playwright                            [예정]
        │
        ▼
⚙️  Core
  ├── Comparator        재고/가격 변동 감지
  ├── AlertHistory      24시간 중복 알림 방지
  └── Notifier          Telegram 발송
        │
        ▼
💾 Storage (Phase 1: GitHub repo JSON / Phase 2+: AWS DynamoDB + S3)
        │
        ▼
📱 Telegram 알림
```

---

## 빠른 시작

### 사전 요구사항

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (패키지 매니저)
- Telegram Bot Token ([BotFather](https://t.me/botfather)에서 발급)

### 1. 저장소 클론 및 의존성 설치

```bash
git clone https://github.com/veryfaraway/DeReel.git
cd dereel
uv sync
uv run playwright install chromium --with-deps
```

### 2. 환경변수 설정

```bash
cp .env.example .env
# TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 입력
```

> Telegram Chat ID 확인: [@userinfobot](https://t.me/userinfobot)에 아무 메시지나 보내면 확인 가능

### 3. 감시 대상 설정

설정 파일은 감시 유형별로 분리되어 있습니다:

| 파일 | 대상 |
|---|---|
| `config/stock.yaml` | 재고 감시 (Apple 리퍼비시) |
| `config/games.yaml` | 게임 가격·무료 감시 (Steam, GOG, Epic) |
| `config/shopping.yaml` | 쇼핑몰 가격 감시 (Amazon, 쿠팡 — 예정) |

**가격 감시 예시** (`config/games.yaml`):

```yaml
targets:
  - site: steam
    type: price
    interval_hours: 3
    currency: KRW
    enabled: true
    dry_run: false
    products:
      - app_id: "1245620"
        name: "Elden Ring"
        target_price: 33000
      - bundle_id: "6588"
        name: "Monkey Island Collection"
        target_price: 20000
```

**Epic 무료 게임 watchlist 예시**:

```yaml
  - site: epic
    type: price
    interval_hours: 6
    currency: KRW
    enabled: true
    dry_run: false
    products: []               # 비워두면 전체 무료 게임 알림
    # watchlist:
    # products:
    #   - slug: "transistor"
    #     name: "Transistor"
    #     target_price: 0
```

자세한 설정 방법은 [TARGETS_GUIDE.md](./docs/TARGETS_GUIDE.md)를 참고한다.

### 4. 로컬 동작 확인

```bash
# 전체 크롤러 실행 (config/*.yaml 자동 탐색)
uv run python -m dereel.run

# 특정 설정 파일만 실행
uv run python -m dereel.run --config config/games.yaml
```

### 5. GitHub Actions 배포

1. GitHub repo → **Settings → Secrets and variables → Actions** 에서 등록:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
2. repo → **Actions → DeReel — 크롤링 → Run workflow** 로 수동 실행

자세한 배포 절차는 [DEPLOYMENT.md](./docs/DEPLOYMENT.md)를 참고한다.

---

## 프로젝트 구조

```text
dereel/
├── .github/
│   └── workflows/
│       └── crawl.yml             통합 크롤러 (매시간, interval_hours로 제어)
├── config/
│   ├── stock.yaml                재고 감시 (apple_refurb)
│   ├── games.yaml                게임 가격/무료 감시 (steam, gog, epic)
│   └── shopping.yaml             쇼핑 가격 감시 (amazon, coupang — 예정)
├── dereel/
│   ├── core/                     핵심 모듈 (비교, 알림, 저장, 스케줄)
│   ├── crawlers/                 사이트별 크롤러
│   ├── models/                   데이터 모델
│   └── run.py                    엔트리포인트
├── data/                         상태 파일 (GHA가 자동 커밋)
├── tests/                        단위 테스트
└── docs/                         설계 문서
```

---

## 문서

| 문서 | 설명 |
|---|---|
| [PRD.md](./docs/PRD.md) | 제품 요구사항 정의서 |
| [FEATURES.md](./docs/FEATURES.md) | 기능 목록 및 Phase 로드맵 |
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 시스템 아키텍처 |
| [TARGETS_GUIDE.md](./docs/TARGETS_GUIDE.md) | 설정 파일 가이드 |
| [CRAWLING_STRATEGY.md](./docs/CRAWLING_STRATEGY.md) | 사이트별 크롤링 전략 |
| [DATA_SCHEMA.md](./docs/DATA_SCHEMA.md) | 데이터 모델 및 스키마 |
| [NOTIFICATION_SPEC.md](./docs/NOTIFICATION_SPEC.md) | 알림 유형 및 메시지 포맷 |
| [DEV_SETUP.md](./docs/DEV_SETUP.md) | 개발 환경 설정 가이드 |
| [HOW_TO_ADD_CRAWLER.md](./docs/HOW_TO_ADD_CRAWLER.md) | 새 크롤러 추가 가이드 |
| [DEPLOYMENT.md](./docs/DEPLOYMENT.md) | 배포 절차 |
| [RUNBOOK.md](./docs/RUNBOOK.md) | 운영 런북 (장애 대응) |

---

## 개발

```bash
# 테스트 실행
uv run pytest

# 코드 품질 검사
uv run ruff check dereel/ tests/
uv run mypy dereel/
```

새 크롤러 추가 방법은 [HOW_TO_ADD_CRAWLER.md](./docs/HOW_TO_ADD_CRAWLER.md)를 참고한다.

---

## Phase 로드맵

```text
✅ Phase 1-A  Apple 리퍼비시 재고 감시 (GitHub Actions + $0)
✅ Phase 1-B  Steam, GOG, Epic 가격/무료 게임 감시
⬜ Phase 2-A  쿠팡, Amazon 감시 + AWS DynamoDB 가격 이력
⬜ Phase 2-B  가격 이력 집계 + Grafana 대시보드
⬜ Phase 3    Kafka 파이프라인 + Vue.js 커스텀 UI
```

---

## 기술 스택

| 항목 | 기술 |
|---|---|
| 언어 | Python 3.13 |
| HTTP 클라이언트 | httpx |
| HTML 파싱 | BeautifulSoup4 |
| 헤드리스 브라우저 | Playwright |
| 데이터 모델 | Pydantic v2 |
| 알림 | python-telegram-bot |
| 로깅 | loguru |
| 패키지 매니저 | uv |
| CI/CD | GitHub Actions |
| 저장소 (Phase 1) | JSON 파일 (GitHub repo) |
| 저장소 (Phase 2+) | AWS DynamoDB + S3 |

---

## 라이선스

MIT License — 개인 사용 및 교육 목적에 한함.  
수집 데이터의 상업적 재판매 금지.

---

## 관련 블로그 포스트

> 이 프로젝트는 풀스택 + 데이터 엔지니어링 학습 과정의 일환으로 제작되었습니다.

- [ ] Phase 1-A 구현기 — GitHub Actions로 무료 크롤링 봇 만들기
- [ ] Phase 1-B 구현기 — Steam/GOG/Epic 가격·무료 게임 감시 크롤러 추가하기
- [ ] Phase 2-A 구현기 — AWS DynamoDB로 가격 이력 저장하기
- [ ] Phase 2-B 구현기 — Grafana로 가격 트렌드 시각화하기
- [ ] Phase 3 구현기 — Kafka + Spark으로 실시간 파이프라인 구축하기
