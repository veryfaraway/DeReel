# DeReel — 알림 명세서

> **버전:** v0.1.0
> **작성일:** 2026-03-31
> **작성자:** 한섭
> **연관 문서:** [FEATURES.md](./FEATURES.md) | [DATA_SCHEMA.md](./DATA_SCHEMA.md)

---

## 1. 알림 시스템 전체 흐름

```
크롤링 결과 (StockResult / PriceResult)
        ↓
[1단계] 변동 감지 (Comparator)
        ↓ 변동 없으면 종료
[2단계] 알림 조건 판단 (AlertEvaluator)
        ↓ 조건 미충족 시 종료
[3단계] 중복 방지 체크 (AlertHistory)
        ↓ 24시간 내 발송 이력 있으면 종료
[4단계] 메시지 포맷 생성 (MessageFormatter)
        ↓
[5단계] 알림 발송 (Notifier → Telegram)
        ↓
[6단계] 발송 이력 저장 (AlertHistory.save)
```

---

## 2. 알림 유형 정의

| 유형 코드 | 이름 | 트리거 조건 | Phase |
|---|---|---|---|
| `stock` | 재고 입고 알림 | `available: false → true` 감지 | 1-A |
| `price` | 가격 하락 알림 | 현재가 ≤ `target_price` | 2-A |
| `discount` | 할인율 알림 | 할인율 ≥ `alert_threshold` | 2-B |
| `free` | 무료 배포 알림 | `is_free: true` 감지 (Epic) | 2-A |
| `struct` | 구조 변경 경보 | 크롤러 파싱 실패 (필드 누락) | 1-A |
| `error` | 크롤러 오류 경보 | 연속 3회 크롤링 실패 | 2-A |

---

## 3. 알림 조건 판단 로직

```python
# dereel/core/alert_evaluator.py

def should_alert_stock(current: StockResult, previous: StockResult | None) -> bool:
    """재고 알림 조건: 이전에 없거나 품절이었던 제품이 입고됨"""
    if previous is None:
        return False                        # 최초 실행 시 알림 없음
    return current.available and not previous.available

def should_alert_price(current: PriceResult, target_price: int | None) -> bool:
    """가격 알림 조건: 현재가가 목표가 이하"""
    if target_price is None:
        return False
    return current.price <= target_price

def should_alert_discount(current: PriceResult, threshold: float | None) -> bool:
    """할인율 알림 조건: 현재 할인율이 임계값 이상"""
    if threshold is None:
        return False
    return current.discount_pct >= threshold

def should_alert_free(current: PriceResult, previous: PriceResult | None) -> bool:
    """무료 배포 알림 조건: 이전에 무료가 아니었던 제품이 무료가 됨"""
    if previous is None:
        return current.is_free
    return current.is_free and not previous.is_free
```

**복합 조건 (price + discount OR 관계)**
```python
def evaluate(current: PriceResult, config: dict) -> list[str]:
    """충족된 알림 유형 목록 반환"""
    alert_types = []

    if should_alert_price(current, config.get("target_price")):
        alert_types.append("price")

    if should_alert_discount(current, config.get("alert_threshold")):
        alert_types.append("discount")

    if should_alert_free(current, previous):
        alert_types.append("free")

    return alert_types  # 비어있으면 알림 없음
```

---

## 4. 중복 방지 로직

```python
# dereel/core/alert_history.py
from datetime import datetime, timezone, timedelta

COOLDOWN_HOURS = 24  # 기본값 (targets.yaml에서 오버라이드 가능)

def can_send(site: str, product_id: str, alert_type: str,
             cooldown_hours: int = COOLDOWN_HOURS) -> bool:
    """
    반환값:
      True  → 발송 가능
      False → 쿨다운 미경과, 발송 스킵
    """
    key = f"{site}:{product_id}:{alert_type}"
    record = history.get(key)

    if record is None:
        return True  # 최초 알림

    last_sent = datetime.fromisoformat(record["last_sent_at"])
    elapsed = datetime.now(timezone.utc) - last_sent
    return elapsed >= timedelta(hours=cooldown_hours)

def record_sent(site: str, product_id: str, alert_type: str) -> None:
    key = f"{site}:{product_id}:{alert_type}"
    history[key] = {
        "last_sent_at": datetime.now(timezone.utc).isoformat(),
        "send_count": history.get(key, {}).get("send_count", 0) + 1,
    }
    storage.save_alert_history(history)
```

**엣지 케이스 처리**

| 상황 | 처리 방식 |
|---|---|
| 입고 → 품절 → 재입고 (24시간 내) | 쿨다운으로 최초 1회만 발송 |
| 목표가 이하 상태가 3시간마다 계속 감지 | 쿨다운으로 1일 1회만 발송 |
| 저장소 접근 실패 (읽기 오류) | 안전하게 발송 스킵 (중복 발송 > 미발송 우선) |
| 저장소 접근 실패 (쓰기 오류) | 발송은 진행, ERROR 로그 기록 |

---

## 5. 메시지 포맷 명세

### 5.1 재고 입고 알림 (`stock`)

```
🍎 [Apple 리퍼비시 입고]

📦 {제품명}
💰 가격: {가격 원화 포맷}
🔗 {상품 URL}

🕐 {감지 시각 KST}
```

**실제 예시**
```
🍎 [Apple 리퍼비시 입고]

📦 AirPods Pro (2세대)
💰 가격: ₩289,000
🔗 https://www.apple.com/kr/shop/product/MQTP3KH/A

🕐 2026-03-31 18:00 KST
```

---

### 5.2 가격 하락 알림 (`price`)

```
💸 [{사이트명}] 가격 알림

🎯 {제품명}
💰 현재가: {현재 가격} (목표가: {목표가})
📉 정가 대비: -{할인율}% ({정가} → {현재가})
🔗 {상품 URL}

🕐 {감지 시각 KST}
```

**실제 예시 — Steam**
```
💸 [Steam] 가격 알림

🎯 Elden Ring
💰 현재가: ₩14,950 (목표가: ₩15,000)
📉 정가 대비: -75% (₩59,800 → ₩14,950)
🔗 https://store.steampowered.com/app/1245620

🕐 2026-03-31 12:00 KST
```

**실제 예시 — 쿠팡**
```
💸 [쿠팡] 가격 알림

🎯 MacBook Air M3 (M3, 8GB, 256GB)
💰 현재가: ₩1,490,000 (목표가: ₩1,500,000)
📉 정가 대비: -12% (₩1,690,000 → ₩1,490,000)
🔗 https://www.coupang.com/vp/products/12345678

🕐 2026-03-31 09:00 KST
```

---

### 5.3 할인율 알림 (`discount`)

```
📉 [{사이트명}] 할인 알림

🎯 {제품명}
🔥 할인율: -{할인율}% (설정 임계값: -{임계값}%)
💰 {정가} → {현재가}
🔗 {상품 URL}

🕐 {감지 시각 KST}
```

**실제 예시 — GOG**
```
📉 [GOG] 할인 알림

🎯 The Witcher 3: Wild Hunt
🔥 할인율: -80% (설정 임계값: -75%)
💰 ₩39,800 → ₩7,960
🔗 https://www.gog.com/game/the_witcher_3_wild_hunt

🕐 2026-03-31 15:00 KST
```

---

### 5.4 무료 배포 알림 (`free`)

```
🎁 [Epic Games] 무료 게임 알림

🎮 {게임명}
🆓 지금 무료! ({무료 종료 시각}까지)
🔗 {상품 URL}

🕐 {감지 시각 KST}
```

**실제 예시**
```
🎁 [Epic Games] 무료 게임 알림

🎮 Satisfactory
🆓 지금 무료! (2026-04-07 22:00 KST까지)
🔗 https://store.epicgames.com/ko/p/satisfactory

🕐 2026-04-01 00:00 KST
```

---

### 5.5 구조 변경 경보 (`struct`)

```
⚠️ [DeReel 경보] 크롤링 구조 변경

🌐 사이트: {사이트명}
❌ 누락 필드: {필드명}
📋 수신된 키: {키 목록}
🕐 {감지 시각 KST}

→ 크롤러 코드 점검이 필요합니다.
```

---

### 5.6 크롤러 오류 경보 (`error`)

```
🚨 [DeReel 경보] 크롤러 연속 실패

🌐 사이트: {사이트명}
💥 오류: {오류 메시지}
🔁 연속 실패 횟수: {횟수}회
🕐 {감지 시각 KST}

→ GitHub Actions 로그를 확인해주세요.
```

---

## 6. 메시지 포맷 유틸리티

```python
# dereel/core/message_formatter.py
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

def fmt_price(amount: int, currency: str = "KRW") -> str:
    """숫자를 통화 포맷으로 변환"""
    if currency == "KRW":
        return f"₩{amount:,}"
    elif currency == "USD":
        return f"${amount / 100:.2f}"   # 센트 → 달러
    elif currency == "JPY":
        return f"¥{amount:,}"
    return f"{amount:,} {currency}"

def fmt_datetime(dt: datetime) -> str:
    """UTC datetime → KST 포맷 문자열"""
    kst_dt = dt.astimezone(KST)
    return kst_dt.strftime("%Y-%m-%d %H:%M KST")

def fmt_url(url: str, site: str) -> str:
    """상품 URL 정리 (불필요한 파라미터 제거)"""
    # 쿠팡 파트너스 URL 변환 (수익 추적 링크 포함)
    if site == "coupang":
        return f"https://link.coupang.com/a/{url.split('/')[-1]}"
    return url
```

---

## 7. Telegram 발송 구현

```python
# dereel/core/notifier.py
import httpx
from dereel.core.settings import settings

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

async def send(message: str, parse_mode: str = "HTML") -> bool:
    """
    Telegram 메시지 발송
    반환값: True = 성공, False = 실패 (재시도 없음)
    """
    url = TELEGRAM_API.format(token=settings.telegram_bot_token.get_secret_value())
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,  # URL 미리보기 활성화
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logger.info(f"Telegram 발송 성공")
            return True
    except Exception as e:
        logger.error(f"Telegram 발송 실패: {e}")
        return False  # 실패해도 프로세스 중단 없음
```

**Telegram API 제약사항**

| 항목 | 제한 | 대응 |
|---|---|---|
| 메시지 최대 길이 | 4,096자 | 초과 시 핵심 정보만 포함한 축약 메시지 발송 |
| 발송 속도 | 30 msg/sec (그룹 기준 20) | DeReel는 소량 발송으로 해당 없음 |
| HTML 태그 | `<b>`, `<i>`, `<a>`, `<code>` 허용 | 현재 Plain Text 사용, 추후 HTML 포맷 전환 검토 |

**메시지 길이 초과 Fallback**
```python
MAX_LENGTH = 4096
TRUNCATED_TEMPLATE = """
{emoji} [{site}] {alert_type_name}

📦 {name}
💰 {price}
🔗 {url}

🕐 {timestamp}
"""

def safe_message(full_msg: str, fallback_data: dict) -> str:
    if len(full_msg) <= MAX_LENGTH:
        return full_msg
    return TRUNCATED_TEMPLATE.format(**fallback_data)
```

---

## 8. 알림 발송 전체 흐름 코드

```python
# dereel/core/alert_pipeline.py

async def process_stock_alert(
    current: StockResult,
    previous: StockResult | None,
    config: dict,
) -> None:
    # 1단계: 변동 감지
    if not should_alert_stock(current, previous):
        return

    # 2단계: 중복 방지
    if not can_send(current.site, current.product_id, "stock",
                    config.get("alert_cooldown_hours", 24)):
        logger.warning(f"알림 스킵 - 24시간 내 중복: {current.name}")
        return

    # 3단계: 메시지 생성
    message = format_stock_message(current)

    # 4단계: 발송
    success = await notifier.send(message)

    # 5단계: 이력 저장 (발송 성공 여부 무관하게 기록)
    if success:
        record_sent(current.site, current.product_id, "stock")


async def process_price_alert(
    current: PriceResult,
    previous: PriceResult | None,
    config: dict,
) -> None:
    # 1단계: 충족된 알림 유형 목록
    alert_types = evaluate(current, previous, config)
    if not alert_types:
        return

    for alert_type in alert_types:
        # 2단계: 중복 방지
        if not can_send(current.site, current.product_id, alert_type,
                        config.get("alert_cooldown_hours", 24)):
            logger.warning(f"알림 스킵 - 중복: {current.name} [{alert_type}]")
            continue

        # 3단계: 메시지 생성
        message = format_price_message(current, alert_type, config)

        # 4단계: 발송
        success = await notifier.send(message)

        # 5단계: 이력 저장
        if success:
            record_sent(current.site, current.product_id, alert_type)
```

---

## 9. Phase 2 확장 — Slack 알림 (예비 설계)

Phase 2-B에서 Slack을 추가할 때 `Notifier` 추상화로 교체 없이 확장한다.

```python
# 확장 구조 (Phase 2-B)
class BaseNotifier(ABC):
    @abstractmethod
    async def send(self, message: str) -> bool: ...

class TelegramNotifier(BaseNotifier):
    async def send(self, message: str) -> bool: ...

class SlackNotifier(BaseNotifier):
    async def send(self, message: str) -> bool: ...

class MultiNotifier(BaseNotifier):
    """복수 채널 동시 발송"""
    def __init__(self, notifiers: list[BaseNotifier]):
        self.notifiers = notifiers

    async def send(self, message: str) -> bool:
        results = await asyncio.gather(
            *[n.send(message) for n in self.notifiers],
            return_exceptions=True,
        )
        return any(r is True for r in results)  # 하나라도 성공이면 True
```

---

## 10. 변경 이력

| 버전 | 날짜 | 내용 | 작성자 |
|---|---|---|---|
| v0.1.0 | 2026-03-31 | 최초 초안 작성 | 한섭 |

