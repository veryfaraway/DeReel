# DeReel

> **Data Extraction & REEL Engine**  
> 크롤링 기반 재고·가격 감시 및 Telegram 알림 시스템

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Cron-2088FF?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/features/actions)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](./LICENSE)

---

## 어떤 프로젝트인가요?

원하는 제품이 입고되거나, 목표 가격 이하로 내려가는 순간  
**Telegram으로 즉시 알림**을 받는 개인용 감시 봇입니다.

```
Apple 리퍼비시 AirPods Pro 2세대 입고!

🍎 [Apple 리퍼비시 입고]

📦 AirPods Pro (2세대)
💰 가격: ₩289,000
🔗 https://www.apple.com/kr/shop/product/MQTP3KH/A

🕐 2026-04-13 20:00 KST
```

서버 없이 **GitHub Actions만으로 동작**하기 때문에 운영 비용이 $0입니다.

---

## 주요 기능

| 기능 | 설명 | Phase |
|---|---|---|
| 🍎 Apple 리퍼비시 재고 감시 | 입고 즉시 Telegram 알림 | 1-A (현재) |
| 💸 Steam 가격 감시 | 목표가 이하 도달 시 알림 | 2-A |
| 🛒 쿠팡 가격 감시 | 파트너스 공식 API 사용 | 2-A |
| 🎮 GOG / Epic 가격 감시 | 할인율 임계값 도달 시 알림 | 2-A |
| 🎁 Epic 무료 게임 알림 | 무료 배포 시작 즉시 알림 | 2-A |
| 📦 Amazon 가격 감시 | Playwright 헤드리스 브라우저 | 2-A |
| 📊 가격 트렌드 대시보드 | Grafana 기반 가격 이력 시각화 | 2-B |

---

## 아키텍처

```
⏰ GitHub Actions Cron
        │
        ▼
🐍 Python Crawler
  ├── apple_refurb.py   (JSON API)
  ├── steam.py          (공식 API)
  ├── coupang.py        (파트너스 API)
  ├── gog.py            (비공식 API)
  ├── epic.py           (GraphQL)
  └── amazon.py         (Playwright)
        │
        ▼
⚙️  Core
  ├── Comparator        재고/가격 변동 감지
  ├── AlertEvaluator    알림 조건 판단
  ├── AlertHistory      24시간 중복 방지
  └── Notifier          Telegram 발송
        │
        ▼
💾 Storage
  Phase 1: GitHub repo JSON 파일   ($0)
  Phase 2: AWS DynamoDB + S3       (~$5/월)
        │
        ▼
📱 Telegram 알림
```

---

## 빠른 시작

### 사전 요구사항

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (패키지 매니저)
- Telegram Bot Token ([BotFather](https://t.me/botfather)에서 발급)

### 1. 저장소 클론 및 의존성 설치

```bash
git clone https://github.com/{username}/dereel.git
cd dereel
uv sync
```

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 값을 입력한다:

```bash
TELEGRAM_BOT_TOKEN=7xxxxxxxxx:AAxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=123456789
```

> Telegram Chat ID 확인 방법: [@userinfobot](https://t.me/userinfobot)에 아무 메시지나 보내면 확인 가능

### 3. 감시 대상 설정

```yaml
# config/targets.yaml
crawlers:
  apple_refurb:
    enabled: true          # ← true로 변경
    interval_hours: 4
    categories:
      - airpods            # 감시할 카테고리
      # - mac
      # - iphone
```

### 4. 드라이런으로 동작 확인

```bash
# 알림 발송 없이 결과만 출력
uv run python -m dereel.run --type stock --dry-run
```

### 5. GitHub Actions 배포

```bash
# GitHub Secrets 등록 후 수동 트리거
# repo → Actions → "Crawl Stock" → Run workflow
```

자세한 배포 절차는 [DEPLOYMENT.md](./docs/DEPLOYMENT.md)를 참고한다.

---

## 프로젝트 구조

```
dereel/
├── .github/workflows/      GitHub Actions 워크플로
├── config/
│   └── targets.yaml        감시 대상 및 조건 설정
├── dereel/
│   ├── core/               핵심 모듈 (비교, 알림, 저장)
│   ├── crawlers/           사이트별 크롤러
│   └── models/             데이터 모델
├── data/                   상태 파일 (자동 관리)
├── tests/                  단위 테스트
└── docs/                   설계 문서
```

---

## 문서

| 문서 | 설명 |
|---|---|
| [PRD.md](./docs/PRD.md) | 제품 요구사항 정의서 |
| [FEATURES.md](./docs/FEATURES.md) | 기능 목록 및 Phase 로드맵 |
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 시스템 아키텍처 |
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
uv run black dereel/ tests/
uv run ruff check dereel/ tests/
uv run mypy dereel/

# 특정 사이트 드라이런
uv run python -m dereel.run --type stock --site apple_refurb --dry-run --log-level DEBUG
```

새 크롤러를 추가하는 방법은 [HOW_TO_ADD_CRAWLER.md](./docs/HOW_TO_ADD_CRAWLER.md)를 참고한다.

---

## Phase 로드맵

```
✅ Phase 1-A  Apple 리퍼비시 재고 감시 (GitHub Actions + $0)
⬜ Phase 2-A  Steam, 쿠팡, GOG, Epic, Amazon 가격 감시 + AWS
⬜ Phase 2-B  가격 이력 집계 + Grafana 대시보드
⬜ Phase 3    Kafka 파이프라인 + Vue.js 커스텀 UI
```

---

## 기술 스택

| 항목 | 기술 |
|---|---|
| 언어 | Python 3.11 |
| HTTP 클라이언트 | httpx |
| 헤드리스 브라우저 | Playwright |
| 데이터 모델 | Pydantic v2 |
| 알림 | python-telegram-bot |
| 로깅 | loguru |
| 패키지 매니저 | uv |
| CI/CD | GitHub Actions |
| 저장소 (Phase 1) | JSON 파일 |
| 저장소 (Phase 2+) | AWS DynamoDB + S3 |

---

## 라이선스

MIT License — 개인 사용 및 교육 목적에 한함.  
수집 데이터의 상업적 재판매 금지.

---

## 관련 블로그 포스트

> 이 프로젝트는 풀스택 + 데이터 엔지니어링 학습 과정의 일환으로 제작되었습니다.

- [ ] Phase 1-A 구현기 — GitHub Actions로 무료 크롤링 봇 만들기
- [ ] Phase 2-A 구현기 — AWS DynamoDB로 가격 이력 저장하기
- [ ] Phase 2-B 구현기 — Grafana로 가격 트렌드 시각화하기
- [ ] Phase 3 구현기 — Kafka + Spark으로 실시간 파이프라인 구축하기
