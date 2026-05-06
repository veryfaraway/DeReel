# DeReel — targets.yaml 설정 가이드

> **연관 문서:** [HOW_TO_ADD_CRAWLER.md](./HOW_TO_ADD_CRAWLER.md) | [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 개요

`config/targets.yaml`은 DeReel의 모든 크롤링 동작을 제어하는 중앙 설정 파일이다.  
**코드를 수정하지 않고** 이 파일만 편집해서 감시 대상을 추가/수정/비활성화할 수 있다.

---

## 전체 구조

```yaml
targets:
  - site: <크롤러 ID>        # 필수 — CRAWLER_REGISTRY 키와 일치해야 함
    type: stock | price      # 필수 — 크롤러 종류
    interval_hours: <숫자>   # 필수 — 크롤링 간격 (시간)
    url: <URL>               # 사이트별 필수 여부 다름
    enabled: true | false    # 선택 (기본: true)
    dry_run: true | false    # 선택 (기본: false)
```

---

## 필드 설명

### `site` (필수)

크롤러를 식별하는 ID. `dereel/run.py`의 `CRAWLER_REGISTRY`에 등록된 키와 정확히 일치해야 한다.

```python
# dereel/run.py
CRAWLER_REGISTRY = {
    "apple_refurb": AppleRefurbCrawler,
    # "steam": SteamCrawler,   # 추후 추가
    # "epic": EpicCrawler,     # 추후 추가
}
```

### `type` (필수)

크롤러의 동작 유형. GHA 워크플로와 연결된다.

| 값 | 설명 | 연결 워크플로 |
|---|---|---|
| `stock` | 재고 변동 감시 (입고/품절) | `crawl_stock.yml` |
| `price` | 가격 변동 감시 (목표가, 할인율) | `crawl_price.yml` |

### `interval_hours` (필수)

크롤링 최소 간격 (시간 단위). GHA는 매시간 실행되지만, 마지막 크롤링 시각 기준으로 `interval_hours`가 경과하지 않으면 스킵된다.

```
GHA 매시간 실행
  → interval_hours: 4 설정 시 → 4회 중 3회 스킵, 1회만 실제 크롤링
```

> ⚠️ GHA cron 최소 단위가 1시간이므로 `interval_hours: 1` 미만은 의미 없다.

**사이트별 권장 값:**

| 사이트 | 권장 `interval_hours` | 이유 |
|---|---|---|
| apple_refurb | 4 | 재고 변동이 잦지 않음 |
| steam | 3 | 특가 감지 적시성 |
| epic | 6 | 무료 게임은 주 단위 변경 |
| amazon | 12 | 가격 변동 느림 + 차단 리스크 |

### `url` (크롤러별 필수)

크롤링 대상 URL. 동일 `site`에 URL이 다르면 **별도 스케줄**로 독립 관리된다.  
스케줄 키는 `{site}:{url}` 조합으로 생성된다.

```yaml
# ipad와 mac은 별도 스케줄로 관리됨
- site: apple_refurb
  url: "https://www.apple.com/kr/shop/refurbished/ipad"
  interval_hours: 4

- site: apple_refurb
  url: "https://www.apple.com/kr/shop/refurbished/mac"
  interval_hours: 4
```

### `enabled` (선택, 기본: `true`)

`false`로 설정하면 해당 항목은 완전히 무시된다.  
크롤러 구현 전 미리 설정을 작성해두거나, 일시적으로 비활성화할 때 사용한다.

```yaml
- site: steam
  enabled: false    # 크롤러 미구현 — 비활성화
```

### `dry_run` (선택, 기본: `false`)

`true`로 설정하면 크롤링은 실행되지만 **Telegram 알림은 발송되지 않는다.**  
새 크롤러 테스트 시 사용한다.

```yaml
- site: epic
  dry_run: true     # 개발 중 — 알림 없이 동작 확인
```

---

## 예시

### Phase 1-A — Apple 리퍼비시만

```yaml
targets:
  - site: apple_refurb
    type: stock
    interval_hours: 4
    url: "https://www.apple.com/kr/shop/refurbished/ipad"
    enabled: true
    dry_run: false

  - site: apple_refurb
    type: stock
    interval_hours: 4
    url: "https://www.apple.com/kr/shop/refurbished/mac"
    enabled: true
    dry_run: false
```

### Phase 1-B — Steam/Epic 추가 예정

```yaml
targets:
  - site: apple_refurb
    type: stock
    interval_hours: 4
    url: "https://www.apple.com/kr/shop/refurbished/ipad"
    enabled: true
    dry_run: false

  - site: steam
    type: price
    interval_hours: 3
    enabled: true
    dry_run: false
    products:
      - product_id: "1245620"
        name: "Elden Ring"
        target_price: 30000

  - site: epic
    type: price
    interval_hours: 6
    enabled: true
    dry_run: false
```

---

## 스케줄 상태 확인

크롤링 실행 시각은 `data/crawl_schedule.json`에 자동 저장된다:

```json
{
  "apple_refurb:https://www.apple.com/kr/shop/refurbished/ipad": 1746380940.603,
  "apple_refurb:https://www.apple.com/kr/shop/refurbished/mac": 1746380943.742
}
```

다음 실행 예정 시각 = 저장된 timestamp + `interval_hours × 3600`

즉시 재실행이 필요하면 해당 키를 삭제하거나 GHA `workflow_dispatch`로 수동 실행한다.

---

## 자주 묻는 질문

**Q. `등록되지 않은 크롤러` 경고가 나와요.**  
→ `dereel/run.py`의 `CRAWLER_REGISTRY`에 해당 `site` 키를 등록해야 한다. [HOW_TO_ADD_CRAWLER.md](./HOW_TO_ADD_CRAWLER.md) 참고.

**Q. `enabled: false`였다가 다시 활성화하면 즉시 실행되나요?**  
→ `data/crawl_schedule.json`에 이전 실행 기록이 남아 있으면 `interval_hours` 체크가 적용된다. 즉시 실행하려면 해당 키를 삭제한다.

---

## 변경 이력

| 버전 | 날짜 | 내용 | 작성자 |
|---|---|---|---|
| v0.1.0 | 2026-05-05 | 최초 작성 | 한섭 |
