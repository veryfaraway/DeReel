
Amazon은 Playwright 의존성 설치 시간이 있어 별도 워크플로로 분리한다.

### 4.2 crawl_stock.yml

```yaml
name: Crawl Stock (Apple Refurb)

on:
  schedule:
    - cron: '0 */4 * * *'    # 4시간마다 (0시, 4시, 8시, 12시, 16시, 20시 UTC)
  workflow_dispatch:           # 수동 실행 (테스트 용도)

jobs:
  crawl:
    runs-on: ubuntu-latest
    permissions:
      contents: write          # data/*.json 커밋을 위해 필요

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run stock crawler
        run: python -m dereel.run --type stock
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}

      - name: Commit state changes
        run: |
          git config user.name "DeReel Bot"
          git config user.email "bot@dereel"
          git add data/
          git diff --staged --quiet || git commit -m "chore: update stock state [skip ci]"
          git push
```

### 4.3 crawl_price.yml

```yaml
name: Crawl Price (Steam / Coupang / GOG / Epic)

on:
  schedule:
    - cron: '0 */3 * * *'    # 3시간마다
  workflow_dispatch:

jobs:
  crawl:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run price crawler
        run: python -m dereel.run --type price
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          COUPANG_ACCESS_KEY: ${{ secrets.COUPANG_ACCESS_KEY }}
          COUPANG_SECRET_KEY: ${{ secrets.COUPANG_SECRET_KEY }}

      - name: Commit state changes
        run: |
          git config user.name "DeReel Bot"
          git config user.email "bot@dereel"
          git add data/
          git diff --staged --quiet || git commit -m "chore: update price state [skip ci]"
          git push
```

### 4.4 crawl_amazon.yml

```yaml
name: Crawl Price (Amazon)

on:
  schedule:
    - cron: '0 */6 * * *'    # 6시간마다
  workflow_dispatch:

jobs:
  crawl:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Install Playwright browsers
        run: playwright install chromium --with-deps

      - name: Run Amazon crawler
        run: python -m dereel.run --type amazon
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}

      - name: Commit state changes
        run: |
          git config user.name "DeReel Bot"
          git config user.email "bot@dereel"
          git add data/
          git diff --staged --quiet || git commit -m "chore: update amazon state [skip ci]"
          git push
```

---

## 5. 크롤링 실패 모니터링

### 5.1 실패 감지 및 알림

```python
# dereel/core/base_crawler.py
def run(self) -> None:
    try:
        raw = self.fetch()
        current = self.parse(raw)
        self.comparator.compare_and_notify(self.site_name, current)
        logger.info(f"{self.site_name} | 크롤링 완료 ({len(current)}개)")
    except Exception as e:
        logger.error(f"{self.site_name} | 크롤링 실패: {e}")
        # 크롤러 실패는 전체 실행을 중단하지 않음
        # Phase 2에서 CloudWatch Alarm 연동
```

### 5.2 구조 변경 감지

크롤러가 예상 필드를 찾지 못할 경우 **구조 변경 경보**를 Telegram으로 발송한다.

```python
STRUCTURE_CHANGE_MESSAGE = """
⚠️ [크롤링 구조 변경 감지]

🌐 사이트: {site_name}
❌ 예상 필드: {expected_field}
📄 실제 응답 키: {actual_keys}
🕐 감지 시각: {timestamp}

→ 크롤러 코드 점검이 필요합니다.
"""
```

---

## 6. 변경 이력

| 버전 | 날짜 | 내용 | 작성자 |
|---|---|---|---|
| v0.1.0 | 2026-03-31 | 최초 초안 작성 | 한섭 |
