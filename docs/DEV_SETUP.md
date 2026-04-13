# DeReel — 개발 환경 설정 가이드

> **버전:** v0.1.0
> **작성일:** 2026-03-31
> **작성자:** 한섭
> **연관 문서:** [ARCHITECTURE.md](./ARCHITECTURE.md) | [CONVENTIONS.md](./CONVENTIONS.md)

---

## 1. 사전 요구사항

| 도구 | 최소 버전 | 확인 명령 | 설치 링크 |
|---|---|---|---|
| Python | 3.11+ | `python --version` | https://python.org |
| Git | 2.40+ | `git --version` | https://git-scm.com |
| uv | 최신 | `uv --version` | https://docs.astral.sh/uv |
| Playwright (Phase 1-B+) | 최신 | `playwright --version` | 아래 참고 |

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

### 2.3 Python 가상환경 생성 및 의존성 설치

```bash
# Python 3.11 가상환경 생성 + 의존성 설치 (한 번에)
uv sync

# 개발 의존성 포함 설치 (테스트, 린트 도구 포함)
uv sync --dev
```

> `uv sync`는 `pyproject.toml`을 읽어 가상환경(`.venv`)을 자동 생성하고  
> 의존성을 설치한다. `pip install -r requirements.txt` 없이 한 번에 완료.

### 2.4 환경변수 설정

```bash
# .env.example을 복사해서 .env 생성
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

### 2.5 Playwright 브라우저 설치 (Amazon 크롤러 사용 시)

```bash
# Playwright 의존성은 uv sync --dev 로 이미 설치됨
# 브라우저만 별도 설치 필요

uv run playwright install chromium --with-deps
```

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
# Bot Token으로 getUpdates 호출 (Bot에 메시지를 한 번 보낸 후 실행)
curl https://api.telegram.org/bot{YOUR_BOT_TOKEN}/getUpdates

# 응답 중 "chat" > "id" 값이 TELEGRAM_CHAT_ID
```

또는 **@userinfobot** 에 메시지를 보내면 본인 Chat ID를 바로 확인 가능.

### 3.3 Bot 연결 테스트

```bash
uv run python -c "
import asyncio
from dereel.core.notifier import send

async def test():
    result = await send('✅ DeReel 알림 테스트 성공!')
    print('발송 결과:', result)

asyncio.run(test())
"
```

---

## 4. 프로젝트 구조 확인

```bash
# 전체 구조 확인
find . -type f -name "*.py" | head -30

# 패키지 설치 확인
uv run python -c "import dereel; print('패키지 로드 성공')"
```

---

## 5. 실행 방법

### 5.1 단일 크롤러 실행 (개발 및 테스트)

```bash
# Apple 리퍼비시 재고 크롤러 실행
uv run python -m dereel.run --type stock --site apple_refurb

# 가격 크롤러 전체 실행
uv run python -m dereel.run --type price

# 특정 사이트만 실행
uv run python -m dereel.run --type price --site steam

# 드라이런 모드 (알림 발송 없이 결과만 출력)
uv run python -m dereel.run --type stock --dry-run
```

### 5.2 실행 옵션 전체 목록

```
usage: python -m dereel.run [options]

옵션:
  --type {stock,price,amazon}   크롤러 유형 (필수)
  --site SITE_NAME              특정 사이트만 실행 (생략 시 전체)
  --dry-run                     알림 발송 없이 결과만 출력
  --log-level {DEBUG,INFO,WARNING,ERROR}
                                로그 레벨 (기본: INFO)
  --config PATH                 targets.yaml 경로 (기본: ./config/targets.yaml)
```

### 5.3 드라이런 예시 출력

```
[2026-03-31 18:00:00 KST] INFO  runner          | 크롤러 시작: stock (apple_refurb)
[2026-03-31 18:00:01 KST] INFO  apple_refurb    | 크롤링 완료 (5개 제품 감지)
[2026-03-31 18:00:01 KST] INFO  comparator      | 신규 입고 감지: AirPods Pro (2세대) [MQTP3KH/A]
[2026-03-31 18:00:01 KST] INFO  notifier        | [DRY-RUN] 알림 발송 스킵
[2026-03-31 18:00:01 KST] INFO  runner          | 완료 (소요시간: 1.2초)
```

---

## 6. 테스트 실행

```bash
# 전체 테스트 실행
uv run pytest

# 특정 파일만 실행
uv run pytest tests/test_comparator.py

# 커버리지 포함 실행
uv run pytest --cov=dereel --cov-report=term-missing

# 상세 출력
uv run pytest -v

# 실패한 테스트만 재실행
uv run pytest --lf
```

**테스트 커버리지 목표**: 핵심 모듈 80% 이상 (NFR 기준)

```bash
# 커버리지 리포트 예시 출력
Name                              Stmts   Miss  Cover
-----------------------------------------------------
dereel/core/comparator.py            42      3    93%
dereel/core/alert_evaluator.py       28      2    93%
dereel/core/notifier.py              18      4    78%
dereel/core/alert_history.py         24      1    96%
dereel/crawlers/apple_refurb.py      35      8    77%
-----------------------------------------------------
TOTAL                               147     18    88%
```

---

## 7. 코드 품질 도구

```bash
# 포맷팅 (black)
uv run black dereel/ tests/

# 린트 (ruff)
uv run ruff check dereel/ tests/

# 린트 자동 수정
uv run ruff check --fix dereel/ tests/

# 타입 체크 (mypy)
uv run mypy dereel/

# 전체 품질 검사 한 번에 (커밋 전 실행 권장)
uv run black dereel/ tests/ && \
uv run ruff check dereel/ tests/ && \
uv run mypy dereel/ && \
uv run pytest --cov=dereel
```

### pre-commit 훅 설정 (선택)

```bash
# pre-commit 설치
uv run pre-commit install

# 수동 실행
uv run pre-commit run --all-files
```

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.3.0
    hooks:
      - id: black

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
```

---

## 8. pyproject.toml 전체 명세

```toml
[project]
name = "dereel"
version = "0.1.0"
description = "Data Extraction & REEL Engine — 크롤링 기반 재고/가격 알림 시스템"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }

dependencies = [
    "httpx>=0.27.0",                  # HTTP 클라이언트 (정적 크롤링)
    "beautifulsoup4>=4.12.0",         # HTML 파싱
    "lxml>=5.1.0",                    # BeautifulSoup 파서
    "playwright>=1.44.0",             # 헤드리스 브라우저 (동적 크롤링)
    "python-telegram-bot>=21.0",      # Telegram 알림
    "pydantic>=2.7.0",                # 데이터 모델 및 유효성 검증
    "pydantic-settings>=2.3.0",       # 환경변수 설정 관리
    "pyyaml>=6.0.1",                  # targets.yaml 파싱
    "boto3>=1.34.0",                  # AWS SDK (Phase 2+)
    "tenacity>=8.3.0",                # 재시도 로직
    "loguru>=0.7.2",                  # 구조화 로깅
]

[project.optional-dependencies]
dev = [
    "pytest>=8.1.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "black>=24.3.0",
    "ruff>=0.3.0",
    "mypy>=1.9.0",
    "pre-commit>=3.7.0",
    "respx>=0.21.0",                  # httpx 모킹 (테스트용)
    "moto>=5.0.0",                    # AWS 서비스 모킹 (테스트용)
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = false
ignore_missing_imports = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["dereel"]
omit = ["tests/*", "dereel/__main__.py"]
```

---

## 9. GitHub Secrets 등록

로컬 `.env`와 별도로, GitHub Actions 실행을 위해 Secrets를 등록해야 한다.

1. GitHub repo → **Settings** → **Secrets and variables** → **Actions**
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

## 10. 로컬에서 GitHub Actions 워크플로 테스트

GitHub에 Push하지 않고 로컬에서 Actions를 시뮬레이션할 수 있다.

```bash
# act 설치 (GitHub Actions 로컬 실행 도구)
# macOS
brew install act

# 워크플로 실행 (dry-run)
act --dryrun

# 실제 실행 (Docker 필요)
act -j crawl -s TELEGRAM_BOT_TOKEN=your_token -s TELEGRAM_CHAT_ID=your_id
```

또는 단순히 **`workflow_dispatch`** 를 이용해 GitHub 웹에서 수동 실행:
1. repo → **Actions** 탭
2. 원하는 워크플로 선택
3. **Run workflow** 버튼 클릭

---

## 11. 자주 발생하는 문제 해결

| 문제 | 원인 | 해결 방법 |
|---|---|---|
| `ModuleNotFoundError: dereel` | 가상환경 미활성화 | `uv sync` 후 `uv run` 접두사 사용 |
| `ValidationError: telegram_bot_token` | `.env` 파일 없음 | `cp .env.example .env` 후 값 입력 |
| `playwright._impl._errors.Error` | 브라우저 미설치 | `uv run playwright install chromium` |
| `httpx.ConnectTimeout` | 네트워크 문제 또는 IP 차단 | VPN 전환 또는 다음 주기 대기 |
| `git commit` 실패 (Actions) | repo 쓰기 권한 없음 | Actions 설정 → `permissions: contents: write` 확인 |
| `ruff: E501 line too long` | 라인 길이 초과 | `black` 실행 후 재시도 |

---

## 12. 변경 이력

| 버전 | 날짜 | 내용 | 작성자 |
|---|---|---|---|
| v0.1.0 | 2026-03-31 | 최초 초안 작성 | 한섭 |

