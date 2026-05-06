# DeReel — 개발 환경 설정 가이드

> **버전:** v0.2.0
> **작성일:** 2026-05-05
> **작성자:** 한섭
> **연관 문서:** [ARCHITECTURE.md](./ARCHITECTURE.md) | [CONVENTIONS.md](./CONVENTIONS.md)

---

## 1. 사전 요구사항

| 도구 | 최소 버전 | 확인 명령 | 설치 링크 |
|---|---|---|---|
| Python | 3.13+ | `python --version` | https://python.org |
| Git | 2.40+ | `git --version` | https://git-scm.com |
| uv | 최신 | `uv --version` | https://docs.astral.sh/uv |

> 💡 패키지 매니저로 `pip` 대신 **`uv`** 를 사용한다.
> `uv`는 pip보다 10~100배 빠르며, 가상환경과 의존성 관리를 통합한다.

---

## 2. 초기 설정 (최초 1회)

### 2.1 저장소 클론

```bash
git clone https://github.com/{username}/dereel.git
cd dereel
```

### 2.2 uv 설치 (미설치 시)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 설치 확인
uv --version
```

### 2.3 의존성 설치

```bash
# 의존성 설치 (가상환경 자동 생성)
uv sync

# 개발 의존성 포함 (테스트, 린트 도구)
uv sync --dev
```

### 2.4 Playwright 브라우저 설치

Phase 1-A부터 Apple 리퍼비시 크롤러에 Playwright를 사용한다. 반드시 설치해야 한다.

```bash
uv run playwright install chromium --with-deps
```

### 2.5 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 실제 값을 입력한다:

```bash
# .env
TELEGRAM_BOT_TOKEN=7xxxxxxxxx:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=123456789

# 쿠팡 파트너스 (Phase 2-A에서 사용)
COUPANG_ACCESS_KEY=
COUPANG_SECRET_KEY=

# AWS (Phase 2-A에서 사용)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=ap-northeast-2
```

> ⚠️ `.env` 파일은 `.gitignore`에 등록되어 있어 repo에 커밋되지 않는다.
> 절대로 실제 토큰/키 값을 코드에 직접 작성하거나 커밋하지 않는다.

---

## 3. Telegram Bot 설정

### 3.1 Bot 생성

1. Telegram에서 **@BotFather** 검색 후 대화 시작
2. `/newbot` 명령 입력
3. Bot 이름 입력 (예: `DeReel Alert`)
4. Bot 사용자명 입력 (예: `dereel_alert_bot`) — `_bot`으로 끝나야 함
5. 발급된 **HTTP API Token** 복사 → `.env`의 `TELEGRAM_BOT_TOKEN`에 입력

### 3.2 Chat ID 확인

```bash
# Bot에 메시지를 한 번 보낸 후 실행
curl https://api.telegram.org/bot{YOUR_BOT_TOKEN}/getUpdates
# 응답 중 "chat" > "id" 값이 TELEGRAM_CHAT_ID
```

또는 **@userinfobot** 에 메시지를 보내면 본인 Chat ID를 바로 확인 가능.

---

## 4. 실행 방법

### 4.1 실행 옵션

```
usage: python -m dereel.run [options]

옵션:
  --type {stock,price}   크롤러 유형 (필수)
                           stock: 재고 변동 감시 (Apple 리퍼비시 등)
                           price: 가격 변동 감시 (Steam, Epic 등)
```

### 4.2 실행 예시

```bash
# 재고 크롤러 실행
uv run python -m dereel.run --type stock

# 가격 크롤러 실행
uv run python -m dereel.run --type price
```

> 알림 없이 테스트하려면 `config/targets.yaml`에서 해당 항목의 `dry_run: true`로 설정한다.

### 4.3 스케줄 동작 방식

GHA는 매시간 실행되지만 실제 크롤링은 `targets.yaml`의 `interval_hours` 기준으로 제어된다.
로컬에서 즉시 재실행하려면 `data/crawl_schedule.json`에서 해당 키를 삭제한다.

```bash
# 스케줄 상태 확인
cat data/crawl_schedule.json

# 특정 항목 즉시 재실행 (스케줄 초기화)
echo '{}' > data/crawl_schedule.json
```

---

## 5. 테스트 실행

```bash
# 전체 테스트
uv run pytest

# 특정 파일만
uv run pytest tests/test_comparator.py

# 커버리지 포함
uv run pytest --cov=dereel --cov-report=term-missing

# 상세 출력
uv run pytest -v

# 실패한 테스트만 재실행
uv run pytest --lf
```

**테스트 커버리지 목표**: 핵심 모듈 80% 이상 (NFR 기준)

---

## 6. 코드 품질 도구

```bash
# 린트 (ruff)
uv run ruff check dereel/ tests/

# 린트 자동 수정
uv run ruff check --fix dereel/ tests/

# 타입 체크 (mypy)
uv run mypy dereel/

# 커밋 전 전체 검사
uv run ruff check dereel/ tests/ && \
uv run mypy dereel/ && \
uv run pytest --cov=dereel
```

### pre-commit 훅 설정 (선택)

```bash
uv run pre-commit install

# 수동 실행
uv run pre-commit run --all-files
```

---

## 7. pyproject.toml 전체 명세

```toml
[project]
name = "dereel"
version = "0.1.0"
description = "Data Extraction & REEL Engine — 크롤링 기반 재고/가격 알림 시스템"
readme = "README.md"
requires-python = ">=3.13"
license = { text = "MIT" }

dependencies = [
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.1.0",
    "playwright>=1.44.0",
    "python-telegram-bot>=21.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "pyyaml>=6.0.1",
    "boto3>=1.34.0",         # Phase 2+
    "tenacity>=8.3.0",
    "loguru>=0.7.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.1.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.3.0",
    "mypy>=1.9.0",
    "pre-commit>=3.7.0",
    "respx>=0.21.0",
    "moto>=5.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py313"
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.13"
strict = false
ignore_missing_imports = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["dereel"]
omit = ["tests/*"]
```

---

## 8. GitHub Secrets 등록

로컬 `.env`와 별도로, GitHub Actions 실행을 위해 Secrets를 등록해야 한다.

1. GitHub repo → **Settings → Secrets and variables → Actions**
2. **New repository secret** 클릭
3. 아래 목록을 순서대로 등록:

| Secret 이름 | 값 | 필요 Phase |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather에서 발급받은 토큰 | 1-A~ |
| `TELEGRAM_CHAT_ID` | 본인 Chat ID | 1-A~ |
| `COUPANG_ACCESS_KEY` | 파트너스 Access Key | 2-A~ |
| `COUPANG_SECRET_KEY` | 파트너스 Secret Key | 2-A~ |
| `AWS_ACCESS_KEY_ID` | IAM 사용자 Access Key | 2-A~ |
| `AWS_SECRET_ACCESS_KEY` | IAM 사용자 Secret Key | 2-A~ |

---

## 9. 로컬에서 GitHub Actions 테스트

```bash
# act 설치 (macOS)
brew install act

# 워크플로 dry-run
act --dryrun

# 실제 실행 (Docker 필요)
act -j crawl -s TELEGRAM_BOT_TOKEN=your_token -s TELEGRAM_CHAT_ID=your_id
```

또는 GitHub 웹에서 수동 실행:
1. repo → **Actions** 탭
2. 원하는 워크플로 선택
3. **Run workflow** 클릭

---

## 10. 자주 발생하는 문제 해결

| 문제 | 원인 | 해결 방법 |
|---|---|---|
| `ModuleNotFoundError: bs4` | beautifulsoup4 미설치 | `uv add beautifulsoup4` |
| `ModuleNotFoundError: dereel` | 가상환경 미활성화 | `uv sync` 후 `uv run` 접두사 사용 |
| `ValidationError: telegram_bot_token` | `.env` 파일 없음 | `cp .env.example .env` 후 값 입력 |
| `InvalidToken` (GHA) | GitHub Secrets 미등록 | repo Settings → Secrets 등록 확인 |
| `playwright._impl._errors.Error` | 브라우저 미설치 | `uv run playwright install chromium --with-deps` |
| `NoneType is not iterable` | 재고 없는 카테고리 | 정상 동작 — `tiles: null`은 재고 0건을 의미 |
| `git commit` 실패 (Actions) | repo 쓰기 권한 없음 | 워크플로에 `permissions: contents: write` 확인 |

---

## 11. 변경 이력

| 버전 | 날짜 | 내용 | 작성자 |
|---|---|---|---|
| v0.1.0 | 2026-03-31 | 최초 초안 작성 | 한섭 |
| v0.2.0 | 2026-05-05 | Python 3.13 반영, 실행 옵션 업데이트, Playwright Phase 1-A 필수로 변경, 트러블슈팅 추가 | 한섭 |
