# Changelog

> 이 프로젝트는 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다.

---

## [0.2.0] — 2026-05-05

### Added

- `config/targets.yaml`에 `type`, `interval_hours`, `enabled`, `dry_run` 필드 추가
- `dereel/run.py` — `--type stock|price` 인자로 크롤러 유형 분리 실행
- `dereel/core/storage.py` — `get_last_crawled_at` / `save_crawled_at` 메서드 추가
- `data/crawl_schedule.json` — 사이트별 마지막 크롤링 실행 시각 저장
- `.github/workflows/crawl_stock.yml` — 재고 크롤러 GHA 워크플로 (매시간)
- `.github/workflows/crawl_price.yml` — 가격 크롤러 GHA 워크플로 (매시간, 30분 offset)
- `docs/TARGETS_GUIDE.md` — targets.yaml 설정 가이드 신규 작성

### Changed

- GHA 실행 주기: 고정 4h/3h → **매시간 실행 + `interval_hours`로 사이트별 제어**
- `crawlers/apple_refurb.py` — `tiles: null` 처리 (`or []`로 재고 0건 정상 처리)
- `docs/README.md` — 현재 구현 기준으로 전면 업데이트
- `docs/ARCHITECTURE.md` — Phase 1-A 다이어그램, Storage 파일 구조 업데이트
- `docs/DEV_SETUP.md` — Python 3.13, 실행 옵션, Playwright 필수 시점 업데이트

### Fixed

- Mac 리퍼비시 재고 없을 때 `NoneType is not iterable` 오류 수정

---

## [0.1.0] — 2026-04-13

### Added

- Apple 리퍼비시 재고 크롤러 (`dereel/crawlers/apple_refurb.py`)
  - Playwright + `window.REFURB_GRID_BOOTSTRAP` Bootstrap JSON 파싱
  - iPad / Mac 카테고리 지원
- 재고 변동 감지 (`dereel/core/comparator.py`)
  - 신규 입고 = 현재 목록 - 이전 스냅샷
- 24시간 중복 알림 방지 (`dereel/core/alert_history.py`)
- Telegram 알림 발송 (`dereel/core/notifier.py`)
- JSON 파일 기반 상태 저장 (`dereel/core/storage.py`)
- 환경변수 관리 (`dereel/core/settings.py`, pydantic-settings)
- 재고 결과 데이터 모델 (`dereel/models/stock_result.py`)
- 설계 문서 초안 전체 작성 (PRD, ARCHITECTURE, FEATURES 등)

---

## 변경 이력 작성 규칙

| 섹션 | 설명 |
|---|---|
| `Added` | 새로운 기능 추가 |
| `Changed` | 기존 기능 변경 |
| `Fixed` | 버그 수정 |
| `Deprecated` | 곧 제거될 기능 |
| `Removed` | 제거된 기능 |
| `Security` | 보안 관련 수정 |
