# CHANGELOG.md
# DeReel — 변경 이력

모든 주목할 만한 변경 사항은 이 문서에 기록한다.  
[Keep a Changelog](https://keepachangelog.com/ko/1.0.0/) 형식을 따르며,  
[Semantic Versioning](https://semver.org/lang/ko/) 규칙에 따라 버전을 관리한다.

---

## 버전 규칙

```
v{MAJOR}.{MINOR}.{PATCH}

MAJOR: 하위 호환이 불가능한 변경 (데이터 구조 파괴적 변경, Phase 전환)
MINOR: 하위 호환 가능한 기능 추가 (새 크롤러, 새 알림 유형)
PATCH: 버그 수정, 설정 변경, 문서 업데이트
```

### 변경 유형

| 태그 | 설명 |
|---|---|
| `Added` | 새로운 기능 추가 |
| `Changed` | 기존 기능 변경 |
| `Deprecated` | 곧 제거될 기능 |
| `Removed` | 제거된 기능 |
| `Fixed` | 버그 수정 |
| `Security` | 보안 취약점 수정 |

---

## [Unreleased]

> 아직 릴리즈되지 않은 변경 사항을 여기에 기록한다.  
> 릴리즈 시 버전 헤더로 이동한다.

### Added
- 프로젝트 초기 문서 작성 완료 (PRD, FEATURES, NFR, ARCHITECTURE 등 14개)

---

## [0.1.0] — 2026-04-13

> **Phase 1-A MVP** — Apple 리퍼비시 재고 감시 + Telegram 알림

### Added
- Apple 리퍼비시 재고 크롤러 (`dereel/crawlers/apple_refurb.py`)
  - 비공개 JSON API 방식 (`product-locator-meta`)
  - 카테고리별 감시 (airpods, mac, iphone, ipad, applewatch)
  - 신규 입고 감지 (품절 → 재고 있음 전환 시 알림)
- `BaseCrawler` 추상 기반 클래스 (`dereel/core/base_crawler.py`)
  - `fetch()` / `parse()` / `format_message()` 인터페이스 정의
  - `run()` 공통 실행 흐름 (크롤링 → 비교 → 알림)
- `Comparator` — 재고 변동 감지 로직 (`dereel/core/comparator.py`)
- `Notifier` — Telegram 알림 발송 (`dereel/core/notifier.py`)
  - 4,096자 초과 시 축약 메시지 Fallback
- `AlertHistory` — 24시간 중복 알림 방지 (`dereel/core/alert_history.py`)
- `Storage` — JSON 파일 기반 상태 저장 (`dereel/core/storage.py`)
  - `JsonFileStorage` 구현체
  - Phase 2 전환 대비 추상 인터페이스 정의
- `Settings` — pydantic-settings 기반 환경변수 관리 (`dereel/core/settings.py`)
- `StockResult` 데이터 모델 (`dereel/models/stock_result.py`)
- `MessageFormatter` 유틸리티 (`dereel/core/message_formatter.py`)
  - `fmt_price()` — 원화/달러/엔 포맷 변환
  - `fmt_datetime()` — UTC → KST 문자열 변환
- `targets.yaml` 설정 스키마 및 초기값 (`config/targets.yaml`)
- GitHub Actions 워크플로 3개
  - `crawl_stock.yml` — 4시간 주기 재고 크롤링
  - `crawl_price.yml` — 3시간 주기 가격 크롤링 (Phase 2-A 대비)
  - `crawl_amazon.yml` — 6시간 주기 Amazon 크롤링 (Phase 2-A 대비)
- 프로젝트 문서 14개 (`docs/` 디렉토리)
  - PRD.md, FEATURES.md, NFR.md, ARCHITECTURE.md
  - CRAWLING_STRATEGY.md, DATA_SCHEMA.md, NOTIFICATION_SPEC.md
  - DEV_SETUP.md, CONVENTIONS.md, HOW_TO_ADD_CRAWLER.md
  - DEPLOYMENT.md, RUNBOOK.md, CHANGELOG.md, README.md
- `pyproject.toml` 프로젝트 설정 (uv 기반)
- `.env.example` 환경변수 템플릿
- `.gitignore` (`.env`, `data/*.json` 제외 설정)

### 기술 스택

| 항목 | 선택 |
|---|---|
| 언어 | Python 3.11 |
| HTTP 클라이언트 | httpx 0.27 |
| 알림 | python-telegram-bot 21 |
| 데이터 모델 | pydantic v2 |
| 설정 관리 | pydantic-settings |
| 로깅 | loguru |
| 패키지 매니저 | uv |
| CI/CD | GitHub Actions |
| 상태 저장 | JSON 파일 (GitHub repo) |

---

## 로드맵 (예정)

> 아래 항목은 확정된 릴리즈가 아니며, 우선순위에 따라 변경될 수 있다.

### [0.2.0] — Phase 2-A 예정
- [ ] Steam 가격 크롤러 (공식 Store API)
- [ ] 쿠팡 파트너스 가격 크롤러 (공식 API + HMAC 인증)
- [ ] GOG 가격 크롤러 (비공식 API + HTML Fallback)
- [ ] Epic Games 가격 크롤러 + 무료 게임 알림
- [ ] Amazon 가격 크롤러 (Playwright)
- [ ] `PriceResult` 데이터 모델
- [ ] 가격 하락 알림 (`price`, `discount`, `free` 유형)
- [ ] AWS DynamoDB 가격 이력 저장 (`DynamoDBStorage` 구현체)
- [ ] AWS S3 상태 스냅샷 저장

### [0.3.0] — Phase 2-B 예정
- [ ] 월별/연별 가격 집계 배치 (Lambda)
- [ ] Grafana 대시보드 (Lightsail)
  - 가격 트렌드 차트
  - 재고 타임라인
- [ ] `targets.yaml` 웹 UI (감시 목록 CRUD)
- [ ] AWS CloudWatch 알람 연동 (연속 3회 실패 → Telegram 경보)

### [1.0.0] — Phase 3 예정
- [ ] Apache Kafka 파이프라인 (Lightsail EC2 자체 설치)
- [ ] Spark Streaming 가격 트렌드 분석
- [ ] Vue.js + Spring Boot 커스텀 대시보드
- [ ] 멀티유저 지원
- [ ] Slack 알림 채널 추가

---
