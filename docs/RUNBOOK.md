# RUNBOOK.md
# DeReel — 운영 런북

> **버전:** v0.1.0
> **작성일:** 2026-04-13
> **작성자:** 한섭
> **연관 문서:** [DEPLOYMENT.md](./DEPLOYMENT.md) | [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 1. 런북 개요

이 문서는 DeReel 운영 중 발생할 수 있는 **장애, 이상 징후, 정기 점검** 상황에서  
즉시 참조할 수 있는 실행 절차 모음이다.

### 심각도 분류

| 등급 | 기준 | 대응 목표 시간 |
|---|---|---|
| 🔴 **P1** | 알림 시스템 전체 중단 | 1시간 이내 복구 |
| 🟠 **P2** | 특정 크롤러 연속 실패 (3회↑) | 24시간 이내 조치 |
| 🟡 **P3** | 단발 크롤링 실패 / 알림 지연 | 다음 실행 주기 내 자연 해소 |
| 🟢 **P4** | 구조 변경 감지 / 정보성 경보 | 1주일 이내 코드 수정 |

---

## 2. 장애 대응 플로우

```
Telegram 경보 수신 또는 GitHub Actions 실패 이메일
        ↓
[1] GitHub Actions 로그 확인
        ↓
[2] 오류 유형 분류 (아래 섹션 참조)
        ↓
[3] 해당 섹션의 대응 절차 실행
        ↓
[4] 정상 복구 확인 (수동 트리거 → 성공)
        ↓
[5] 원인 기록 (CHANGELOG.md 또는 커밋 메시지)
```

---

## 3. 장애 유형별 대응

---

### 3.1 🔴 P1 — Telegram 알림 전체 중단

**증상:** GitHub Actions는 초록 체크인데 Telegram 알림이 오지 않음

**진단**

```bash
# 1. Bot Token 유효성 확인
curl https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe

# 정상 응답:
# {"ok":true,"result":{"id":...,"is_bot":true,"first_name":"DeReel",...}}

# 실패 응답:
# {"ok":false,"error_code":401,"description":"Unauthorized"}
```

**원인별 해결**

| 원인 | 해결 방법 |
|---|---|
| Bot Token 만료 / 재발급 | BotFather에서 `/revoke` 후 재발급 → GitHub Secrets 업데이트 |
| Chat ID 변경 | @userinfobot으로 재확인 → GitHub Secrets 업데이트 |
| Telegram API 장애 | https://status.telegram.org 확인 → 복구 대기 |
| GitHub Secret 값 오기입 | Secrets 재등록 (값 앞뒤 공백 주의) |

**GitHub Secrets 업데이트 후 검증**

```
GitHub → Actions → "Crawl Stock (Apple Refurb)"
→ Run workflow → 수동 실행
→ Telegram 알림 수신 확인
```

---

### 3.2 🟠 P2 — 특정 크롤러 연속 실패

**증상:** GitHub Actions에서 특정 Step이 빨간 X, 같은 오류가 3회 이상 반복

**진단 절차**

```
GitHub → Actions 탭
→ 실패한 워크플로 클릭
→ "Run stock/price crawler" Step 클릭
→ 로그에서 오류 메시지 확인
```

**오류 메시지별 대응**

#### Case A: HTTP 429 Too Many Requests

```
ERROR  apple_refurb | HTTP 429 - Too Many Requests
```

→ 요청 주기가 너무 짧음

```yaml
# config/targets.yaml 수정
apple_refurb:
  interval_hours: 6    # 4 → 6으로 증가
```

```bash
git commit -m "chore(config): apple_refurb 크롤링 주기 6시간으로 조정"
git push origin main
```

#### Case B: HTTP 403 Forbidden / IP 차단

```
ERROR  amazon | HTTP 403 - Forbidden
```

→ GitHub Actions Runner IP가 차단됨  
→ Amazon은 특히 잦은 차단 발생

```yaml
# 임시 비활성화
amazon:
  enabled: false
```

→ 1~3일 후 재활성화 시도  
→ 반복 차단 시 Playwright stealth 모드 플러그인 도입 검토

#### Case C: 파싱 오류 (구조 변경)

```
ERROR  apple_refurb | 파싱 실패 - KeyError: 'tiles'
⚠️ [DeReel 경보] 크롤링 구조 변경
```

→ 사이트가 API 응답 구조를 변경함  
→ 아래 **3.4 구조 변경 대응** 절차 실행

#### Case D: 타임아웃 연속 발생

```
WARNING  steam | 타임아웃 발생 (30초 초과)
```

→ 사이트 일시 장애이거나 네트워크 문제

```python
# 타임아웃 임시 증가 (dereel/crawlers/steam.py)
TIMEOUT = 45.0   # 30.0 → 45.0
```

→ 커밋 후 다음 주기 정상 여부 확인

---

### 3.3 🟡 P3 — 단발 크롤링 실패

**증상:** 1~2회 실패 후 다음 주기에 자동 정상화

→ **별도 조치 불필요**  
→ GitHub Actions 로그에서 오류 내용만 기록해 두고 모니터링 지속  
→ 같은 오류가 3회 이상 반복되면 P2로 격상

---

### 3.4 🟢 P4 — 크롤링 구조 변경 감지

**증상:** Telegram에 아래 경보 수신

```
⚠️ [DeReel 경보] 크롤링 구조 변경
🌐 사이트: apple_refurb
❌ 누락 필드: 'tiles'
📋 수신된 키: ['results', 'metadata', ...]
```

**대응 절차**

```bash
# 1. 해당 사이트 크롤러 임시 비활성화
# config/targets.yaml
apple_refurb:
  enabled: false
```

```bash
# 2. 현재 실제 응답 구조 확인
curl -s "https://www.apple.com/kr/shop/product-locator-meta?family=airpods"   | python -m json.tool | head -50
```

```bash
# 3. 변경된 구조에 맞게 parse() 수정
# dereel/crawlers/apple_refurb.py

# 기존:
tiles = response["tiles"]

# 변경 후 (예시):
tiles = response["results"]
```

```bash
# 4. 로컬 드라이런으로 검증
uv run python -m dereel.run --type stock --site apple_refurb --dry-run

# 5. 테스트 업데이트 및 실행
uv run pytest tests/crawlers/test_apple_refurb.py -v

# 6. 재활성화 + 커밋
# targets.yaml: enabled: true
git commit -m "fix(crawler): apple_refurb 응답 구조 변경 대응"
git push origin main
```

---

## 4. 정기 점검 절차

### 4.1 주간 점검 (매주 월요일, 5분)

```
□ GitHub Actions → 지난 7일 실행 이력 확인
  → 실패 비율이 20% 이상이면 원인 조사

□ data/stock_state.json 마지막 커밋 시각 확인
  → 4시간 이상 미업데이트이면 워크플로 수동 트리거

□ Telegram 알림 정상 수신 여부 확인
  → 의심스러우면 수동 트리거 후 확인
```

### 4.2 월간 점검 (매월 1일, 15분)

```
□ 의존성 보안 취약점 점검
  uv run pip-audit

□ 크롤러별 성공률 확인
  → Actions 탭에서 지난 30일 실행 이력 검토

□ targets.yaml 감시 목록 유효성 확인
  → 단종된 제품 또는 URL 변경 여부 확인
  → 더 이상 감시 불필요한 제품 제거

□ Phase 2 이후: AWS 비용 확인
  AWS Console → Billing → 이번 달 실제 비용 확인
  → $5 초과 여부 확인, 예상치 못한 항목 점검

□ CHANGELOG.md 업데이트 (지난 달 변경 내역 정리)
```

### 4.3 분기 점검 (3개월마다, 30분)

```
□ Python / 의존성 버전 업그레이드 검토
  uv run python -m pip list --outdated

□ robots.txt 변경 여부 재확인 (사이트별)

□ 크롤링 대상 사이트 ToS 변경 여부 확인

□ 새로 추가할 감시 사이트 검토
  → FEATURES.md Phase 로드맵 참고

□ Phase 전환 필요성 검토
  → 감시 제품 수 100개 초과 → Phase 2 전환 검토
```

---

## 5. 수동 실행 및 유지보수 명령어

### 5.1 워크플로 수동 트리거

```
GitHub → Actions → 워크플로 선택 → Run workflow
```

또는 GitHub CLI 사용:

```bash
# GitHub CLI 설치 후
gh workflow run crawl_stock.yml
gh workflow run crawl_price.yml
gh workflow run crawl_amazon.yml

# 실행 상태 확인
gh run list --limit 5
gh run watch   # 실시간 로그 스트리밍
```

### 5.2 로컬에서 강제 크롤링 (긴급 시)

```bash
# 전체 재고 크롤링 (운영 환경과 동일)
TELEGRAM_BOT_TOKEN=xxx TELEGRAM_CHAT_ID=yyy   uv run python -m dereel.run --type stock

# 특정 사이트만 드라이런
uv run python -m dereel.run --type price --site steam --dry-run --log-level DEBUG
```

### 5.3 상태 파일 초기화

감시 대상을 처음부터 다시 감지하고 싶을 때 (예: 전체 알림 초기화):

```bash
# 재고 상태 초기화 (주의: 다음 실행 시 모든 현재 재고를 신규 입고로 감지)
echo '{}' > data/stock_state.json
git commit -m "chore: stock_state 초기화 [skip ci]"
git push origin main
```

```bash
# 알림 이력만 초기화 (쿨다운 리셋 — 즉시 재알림 가능)
echo '{}' > data/alert_history.json
git commit -m "chore: alert_history 초기화 [skip ci]"
git push origin main
```

> ⚠️ `stock_state.json` 초기화 후 첫 실행 시  
> 현재 재고 있는 모든 제품이 "신규 입고"로 감지되어 대량 알림이 발송될 수 있다.  
> 반드시 `--dry-run`으로 먼저 확인 후 실행할 것.

### 5.4 특정 제품 알림 쿨다운 수동 해제

24시간 쿨다운이 지나기 전에 특정 제품만 즉시 재알림하고 싶을 때:

```bash
# alert_history.json에서 해당 키만 삭제
python3 -c "
import json

with open('data/alert_history.json') as f:
    history = json.load(f)

# 삭제할 키 지정
key = 'apple_refurb:MQTP3KH/A:stock'
if key in history:
    del history[key]
    print(f'삭제 완료: {key}')

with open('data/alert_history.json', 'w') as f:
    json.dump(history, f, indent=2, ensure_ascii=False)
"

git commit -m "chore: alert_history 특정 키 수동 초기화 [skip ci]"
git push origin main
```

---

## 6. Phase 2 운영 명령어

### 6.1 DynamoDB 데이터 확인

```bash
# 특정 제품 전체 이력 조회
aws dynamodb query   --table-name dereel-price-history   --key-condition-expression "PK = :pk"   --expression-attribute-values '{":pk": {"S": "steam:1245620"}}'   --region ap-northeast-2   --output table

# 최신 가격 1건 조회
aws dynamodb query   --table-name dereel-price-history   --key-condition-expression "PK = :pk AND begins_with(SK, :sk)"   --expression-attribute-values '{
    ":pk": {"S": "steam:1245620"},
    ":sk": {"S": "raw#"}
  }'   --scan-index-forward false   --limit 1   --region ap-northeast-2
```

### 6.2 S3 데이터 확인

```bash
# 버킷 내 파일 목록
aws s3 ls s3://dereel-data-{suffix}/ --recursive --human-readable

# 특정 파일 내용 확인
aws s3 cp s3://dereel-data-{suffix}/state/stock_state.json - | python -m json.tool
```

### 6.3 Lambda 로그 확인

```bash
# 최근 1시간 오류 로그
aws logs filter-log-events   --log-group-name /aws/lambda/dereel-crawler   --filter-pattern "ERROR"   --start-time $(python3 -c "import time; print(int((time.time()-3600)*1000))")   --region ap-northeast-2   --output table
```

---

## 7. 긴급 연락 및 에스컬레이션

| 상황 | 조치 |
|---|---|
| Telegram API 전체 장애 | https://status.telegram.org 확인 → 복구 대기 |
| GitHub Actions 전체 장애 | https://www.githubstatus.com 확인 → 복구 대기 |
| AWS 리전 장애 | https://health.aws.amazon.com 확인 → 복구 대기 |
| 의도치 않은 AWS 과금 발생 | AWS Console → Billing → 즉시 해당 리소스 중지 |

---

## 8. 변경 이력

| 버전 | 날짜 | 내용 | 작성자 |
|---|---|---|---|
| v0.1.0 | 2026-04-13 | 최초 초안 작성 | 한섭 |
