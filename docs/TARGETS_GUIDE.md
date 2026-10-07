# DeReel — 크롤링 타겟 설정 및 검증 가이드

> **버전:** v0.2.0  
> **최종 수정일:** 2026-10-08  
> **연관 문서:** [DATA_SCHEMA.md](./DATA_SCHEMA.md) | [HOW_TO_ADD_CRAWLER.md](./HOW_TO_ADD_CRAWLER.md) | [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 1. 개요 및 설정 파일 구조

DeReel은 코드를 수정하지 않고 YAML 설정 파일만으로 감시 대상을 추가/수정/비활성화할 수 있습니다.  
유지보수성과 가독성을 위해 타겟은 **도메인별 설정 파일**로 분리되어 관리됩니다.

```
config/
  ├── games.yaml      # 게임 가격/무료 감시 (Steam, GOG, Epic)
  ├── stock.yaml      # 재고 감시 (Apple 리퍼비시)
  └── shopping.yaml   # 이커머스 쇼핑몰 감시 (추후 지원 예정)
```

* **실행 방식**: [dereel/run.py](file:///Users/ultimate/Workspace/personal/DeReel/dereel/run.py)는 `config/*.yaml`을 자동으로 전체 순회 실행하거나, `--config config/games.yaml`과 같이 특정 파일만 지정해 실행할 수 있습니다.
* **알림 조건**: 가격 감시(`price`)의 경우 `현재 가격 <= target_price`를 만족할 때 Telegram 알림이 발송되며, 24시간 동안 중복 알림이 방지됩니다.

---

## 2. 공통 필드 명세

모든 `config/*.yaml`의 `targets` 항목은 아래 기본 구조를 따릅니다:

```yaml
targets:
  - site: <크롤러 ID>        # 필수 — CRAWLER_REGISTRY 키와 일치 (steam, gog, apple_refurb 등)
    type: stock | price      # 필수 — 크롤러 종류 (재고: stock, 가격: price)
    interval_hours: <숫자>   # 필수 — 크롤링 최소 간격 (시간 단위, 1~24)
    currency: <통화코드>     # 선택 — 기준 통화 (기본: KRW 또는 USD)
    url: <URL>               # stock 타입 필수
    enabled: true | false    # 선택 — 활성화 여부 (기본: true)
    dry_run: true | false    # 선택 — true 시 알림 발송 스킵 (기본: false)
    products: []             # price 타입 필수 — 감시 제품 목록
```

### `interval_hours` 및 스케줄 동작 방식
* GitHub Actions는 매시간 실행되지만, `data/crawl_schedule.json`에 기록된 마지막 크롤링 시각 기준으로 `interval_hours`가 지나지 않은 타겟은 자동으로 건너뜁니다.
* 즉시 재실행이 필요할 경우 `data/crawl_schedule.json`에서 해당 키를 삭제하거나 캐시를 초기화합니다.

---

## 3. Steam 타겟 등록 가이드

Steam은 상품 유형(단일 게임, 패키지, 번들)에 따라 URL 및 파싱 방식이 다릅니다. URL을 확인하고 알맞은 식별자 키 **하나만** 지정합니다.

### 3.1 상품 유형별 식별자 구분

| 상품 유형 | 스토어 URL 패턴 | YAML 식별자 키 | 데이터 수집 방식 |
|---|---|---|---|
| **단일 게임 (App)** | `store.steampowered.com/app/{id}/` | `app_id: "{id}"` | 공식 Store API (`appdetails`) |
| **패키지 (Package/Sub)** | `store.steampowered.com/sub/{id}/` | `package_id: "{id}"` | 공식 Store API (`packagedetails`) |
| **번들 (Bundle)** | `store.steampowered.com/bundle/{id}/` | `bundle_id: "{id}"` | 번들 스토어 HTML 파싱 |

> 💡 **App → Package Fallback**: 사용자가 패키지 ID를 `app_id`로 잘못 등록한 경우, 단일 앱 조회 실패 시 자동으로 Package API 조회를 2차 시도합니다.

### 3.2 Steam 설정 예시 (`config/games.yaml`)

```yaml
targets:
  - site: steam
    type: price
    interval_hours: 3
    currency: KRW
    enabled: true
    dry_run: false
    products:
      # 단일 게임 (App)
      - app_id: "1245620"
        name: "Elden Ring"
        target_price: 33000

      # 번들 (Bundle)
      - bundle_id: "575"
        name: "Sid Meier's Civilization V: Complete"
        target_price: 12000

      # 패키지 (Package)
      - package_id: "2102"
        name: "LucasArts Adventure Pack"
        target_price: 10000
```

---

## 4. GOG 타겟 등록 가이드

GOG는 웹 브라우저 URL에 영문 슬러그(slug)가 노출되지만, 내부 API는 숫자 `product_id`를 사용합니다.

### 4.1 `product_id` 추출 방법

#### 방법 A: 도우미 스크립트 활용 (권장)
[tests/scripts/find_gog_product_ids.py](file:///Users/ultimate/Workspace/personal/DeReel/tests/scripts/find_gog_product_ids.py)를 사용하면 슬러그로부터 `product_id` 추출, 가격 검증 및 YAML 스니펫 생성을 자동화할 수 있습니다:

1. `tests/scripts/find_gog_product_ids.py`의 `SLUGS` 목록에 원하는 게임의 슬러그를 추가합니다:
   ```python
   # 예: https://www.gog.com/en/game/the_witcher_3_wild_hunt
   SLUGS = [
       "the_witcher_3_wild_hunt",
   ]
   ```
2. 스크립트를 실행합니다:
   ```bash
   uv run python tests/scripts/find_gog_product_ids.py
   ```
3. 콘솔에 자동 출력되는 `# targets.yaml 복사용 스니펫`의 내용을 [config/games.yaml](file:///Users/ultimate/Workspace/personal/DeReel/config/games.yaml)에 복사합니다.

#### 방법 B: 웹 브라우저 수동 확인
게임 스토어 페이지 소스 보기에서 `"id":"` 패턴을 검색하여 8~10자리 숫자 ID를 확인합니다.

### 4.2 GOG 설정 예시 (`config/games.yaml`)

```yaml
  - site: gog
    type: price
    interval_hours: 6
    currency: USD            # GOG는 주로 USD 기준
    enabled: true
    dry_run: false
    products:
      - product_id: "1640424747"
        name: "The Witcher 3: Wild Hunt - Complete Edition"
        target_price: 4.99
```

---

## 5. 타겟 검증 절차 (Verification Guide)

타겟을 추가하거나 수정한 후 정상 동작을 확인하는 3단계 검증 절차입니다.

### 1단계: 단위 테스트 실행 (Mock 검증)
크롤러 파서 및 예외 처리 로직에 이상이 없는지 확인합니다:

```bash
# Steam 단위 테스트
uv run pytest tests/crawlers/test_steam.py -v

# GOG 단위 테스트
uv run pytest tests/crawlers/test_gog.py -v
```

### 2단계: 단일 타겟 실시간 수집 검증 (CLI 원라이너)
신규 타겟 ID로 실제 스토어에서 데이터를 가져오는지 즉시 확인합니다:

* **Steam 단일 타겟 확인**:
  ```bash
  uv run python -c "
  import asyncio
  from dereel.crawlers.steam import SteamCrawler
  async def main():
      async with SteamCrawler() as c:
          # bundle_id 확인 예시 (_fetch_app, _fetch_package 가능)
          res = await c._fetch_bundle('575', 'Civ V Complete', 'KRW', 'kr')
          print(res)
  asyncio.run(main())
  "
  ```

* **GOG 단일 타겟 확인**:
  ```bash
  uv run python -c "
  import asyncio
  from dereel.crawlers.gog import GogCrawler
  async def main():
      async with GogCrawler() as c:
          res = await c._fetch_one('1640424747', 'Witcher 3', 'USD', 'US')
          print(res)
  asyncio.run(main())
  "
  ```

### 3단계: 전체 연동 드라이런 (Dry-run) 검증
1. [config/games.yaml](file:///Users/ultimate/Workspace/personal/DeReel/config/games.yaml)에서 테스트할 대상의 `dry_run: true` 여부를 확인합니다.
2. `interval_hours` 스킵을 방지하기 위해 스케줄 캐시를 초기화합니다:
   ```bash
   echo '{}' > data/crawl_schedule.json
   ```
3. 크롤러를 실행하고 로그를 점검합니다:
   ```bash
   uv run python -m dereel.run --config config/games.yaml
   ```
4. **확인 사항**:
   * 각 타겟의 `원가 / 현재가 (할인율)` 로그 정상 출력
   * `[config/games.yaml] 크롤링 완료 ✅` 로그 확인

---

## 6. 자주 묻는 질문 & 트러블슈팅

**Q. Steam 번들 API 호출 시 403 Forbidden 오류가 발생합니다.**  
→ Steam의 `/api/bundledetails` 엔드포인트는 비공개되어 차단됩니다. DeReel의 [SteamCrawler](file:///Users/ultimate/Workspace/personal/DeReel/dereel/crawlers/steam.py)는 `bundle_id` 설정 시 번들 스토어 HTML을 스크래핑해 안전하게 가격을 추출하므로 반드시 `bundle_id` 키를 사용해야 합니다.

**Q. GOG 가격이 정수 문자열(`4990 KRW`)로 옵니다.**  
→ GOG API는 통화에 따라 센트 단위 정수 문자열로 반환합니다. DeReel이 자동으로 `/ 100` 변환하여 처리하므로 `target_price`에는 실제 금액(`49.90` 또는 `3.99`)을 적으면 됩니다.

**Q. 설정을 추가했는데 크롤링이 스킵됩니다.**  
→ `data/crawl_schedule.json`에 이전 실행 기록이 남아 `interval_hours` 체크에 걸린 것입니다. `echo '{}' > data/crawl_schedule.json`으로 스케줄 캐시를 초기화하면 즉시 실행됩니다.

---

## 7. 변경 이력

| 버전 | 날짜 | 내용 | 작성자 |
|---|---|---|---|
| v0.1.0 | 2026-05-05 | 최초 작성 (Apple 리퍼비시 중심) | 한섭 |
| v0.2.0 | 2026-10-08 | `config/*.yaml` 도메인별 분리 반영, Steam(App/Package/Bundle) 및 GOG 타겟 등록 상세화, 단위 테스트/CLI/드라이런 검증 절차 통합 | Antigravity |
