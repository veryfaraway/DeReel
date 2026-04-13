# DEPLOYMENT.md

# DeReel — 배포 가이드

> **버전:** v0.1.0
> **작성일:** 2026-04-13
> **작성자:** 한섭
> **연관 문서:** [ARCHITECTURE.md](./ARCHITECTURE.md) | [DEV_SETUP.md](./DEV_SETUP.md) | [RUNBOOK.md](./RUNBOOK.md)

---

## 1. 배포 전략 개요

DeReel은 Phase별로 배포 방식이 다르다.  
각 Phase는 이전 Phase의 인프라를 **유지한 채** 확장한다.

| Phase | 배포 방식 | 인프라 | 비용 |
|---|---|---|---|
| **1-A** | GitHub Actions (Cron) | GitHub 공개 repo | $0 |
| **1-B** | GitHub Actions (Cron) | GitHub + JSON 파일 | $0 |
| **2-A** | GitHub Actions → AWS Lambda | DynamoDB + S3 | ~$5/월 |
| **2-B** | GitHub Actions → AWS Lambda | + Grafana (Lightsail) | ~$10/월 |
| **3** | AWS ECS / Lambda | Kafka + OpenSearch | ~$50/월 |

> 이 문서는 **Phase 1-A 배포**를 주로 다루고,  
> Phase 2 인프라 프로비저닝 절차는 별도 섹션으로 안내한다.

---

## 2. Phase 1-A 배포 — GitHub Actions

### 2.1 배포 흐름

```
로컬 개발 (DEV_SETUP.md 참고)
        ↓
feat/* 브랜치에서 개발
        ↓
PR 생성 → pytest 통과 확인
        ↓
main 브랜치에 Merge
        ↓
GitHub Actions Cron이 자동 실행
(수동 트리거: workflow_dispatch)
```

### 2.2 최초 배포 체크리스트 (1회)

#### Step 1 — 저장소 공개 여부 확인

```
GitHub repo → Settings → General
→ "Change repository visibility" → Public 확인

⚠️ Private repo는 GitHub Actions 무료 한도(월 2,000분)가 있음
   Phase 1에서는 반드시 Public으로 유지
```

#### Step 2 — GitHub Secrets 등록

```
GitHub repo
→ Settings
→ Secrets and variables
→ Actions
→ New repository secret
```

아래 순서대로 등록한다.

| 순서 | Secret 이름 | 값 출처 |
|---|---|---|
| 1 | `TELEGRAM_BOT_TOKEN` | BotFather 발급 토큰 |
| 2 | `TELEGRAM_CHAT_ID` | @userinfobot으로 확인 |

Phase 2 이후 추가 등록:

| Secret 이름 | 값 출처 |
|---|---|
| `COUPANG_ACCESS_KEY` | 쿠팡 파트너스 API 키 |
| `COUPANG_SECRET_KEY` | 쿠팡 파트너스 API 키 |
| `AWS_ACCESS_KEY_ID` | IAM 사용자 Access Key |
| `AWS_SECRET_ACCESS_KEY` | IAM 사용자 Secret Key |

#### Step 3 — targets.yaml 감시 대상 활성화

```yaml
# config/targets.yaml
crawlers:
  apple_refurb:
    enabled: true        # ← false → true 로 변경
    interval_hours: 4
    categories:
      - airpods
```

커밋 메시지:
```bash
chore(config): Apple 리퍼비시 크롤러 활성화
```

#### Step 4 — 워크플로 파일 확인

```bash
# 워크플로 파일이 존재하는지 확인
ls .github/workflows/
# crawl_stock.yml
# crawl_price.yml
# crawl_amazon.yml
```

#### Step 5 — 수동 트리거로 첫 배포 검증

```
GitHub repo → Actions 탭
→ "Crawl Stock (Apple Refurb)" 선택
→ "Run workflow" 버튼 클릭
→ 실행 결과 확인 (초록 체크 = 성공)
→ Telegram으로 알림 수신 확인
```

첫 실행은 이전 상태가 없어 알림이 발송되지 않는 것이 **정상**이다.  
두 번째 실행부터 변동 감지 시 알림이 발송된다.

#### Step 6 — Cron 스케줄 확인

```yaml
# .github/workflows/crawl_stock.yml
on:
  schedule:
    - cron: '0 */4 * * *'   # UTC 기준 4시간마다
```

> ⚠️ GitHub Actions Cron은 **UTC 기준**이다.  
> `0 */4 * * *` = UTC 0, 4, 8, 12, 16, 20시  
> = KST 9, 13, 17, 21, 1, 5시  
>
> GitHub Actions는 서버 부하에 따라 최대 **30분 지연**될 수 있다.

---

### 2.3 일반 배포 절차 (기능 추가/수정 시)

```bash
# 1. 브랜치 생성
git checkout -b feat/steam-price-crawler

# 2. 개발 + 테스트
uv run pytest
uv run black dereel/ tests/
uv run ruff check dereel/ tests/

# 3. 드라이런 검증
uv run python -m dereel.run --type price --site steam --dry-run

# 4. 커밋
git add .
git commit -m "feat(crawler): Steam 가격 크롤러 구현"

# 5. Push + PR
git push origin feat/steam-price-crawler
# → GitHub에서 PR 생성 → pytest 통과 확인 → main Merge
```

main에 Merge되면 다음 Cron 실행 주기부터 자동 반영된다.

---

### 2.4 배포 확인 방법

| 확인 항목 | 방법 |
|---|---|
| 워크플로 실행 성공 여부 | GitHub → Actions 탭 → 초록 체크 확인 |
| 크롤링 결과 | GitHub → Actions 탭 → 워크플로 로그 확인 |
| 상태 파일 업데이트 | GitHub → `data/stock_state.json` 최근 커밋 시각 확인 |
| Telegram 알림 수신 | Telegram 앱에서 직접 확인 |

---

### 2.5 워크플로 비활성화 (일시 중지)

```
GitHub repo → Actions 탭
→ 비활성화할 워크플로 선택
→ 우측 상단 "..." → "Disable workflow"
```

재활성화 시 동일 경로에서 "Enable workflow" 클릭.

---

## 3. Phase 2-A 배포 — AWS 인프라

### 3.1 사전 요구사항

```bash
# AWS CLI 설치 확인
aws --version

# AWS CLI 설정 (최초 1회)
aws configure
# AWS Access Key ID:     [IAM 키 입력]
# AWS Secret Access Key: [IAM 시크릿 입력]
# Default region name:   ap-northeast-2
# Default output format: json
```

### 3.2 IAM 사용자 생성 및 권한 설정

AWS Console → IAM → 사용자 → 사용자 생성

**사용자명:** `dereel-github-actions`

**필요 권한 (최소 권한 원칙):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:ap-northeast-2:*:table/dereel-*"
    },
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::dereel-*",
        "arn:aws:s3:::dereel-*/*"
      ]
    }
  ]
}
```

생성된 Access Key → GitHub Secrets에 등록 (2.2 Step 2 참고)

### 3.3 DynamoDB 테이블 생성

```bash
# 가격 이력 테이블 생성
aws dynamodb create-table \
  --table-name dereel-price-history \
  --attribute-definitions \
    AttributeName=PK,AttributeType=S \
    AttributeName=SK,AttributeType=S \
  --key-schema \
    AttributeName=PK,KeyType=HASH \
    AttributeName=SK,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region ap-northeast-2

# TTL 활성화 (자동 만료)
aws dynamodb update-time-to-live \
  --table-name dereel-price-history \
  --time-to-live-specification \
    "Enabled=true, AttributeName=ttl" \
  --region ap-northeast-2

# 생성 확인
aws dynamodb describe-table \
  --table-name dereel-price-history \
  --region ap-northeast-2 \
  --query "Table.TableStatus"
```

### 3.4 S3 버킷 생성

```bash
# 버킷 생성 (버킷명은 전 세계 유니크해야 함)
aws s3api create-bucket \
  --bucket dereel-data-{your-unique-suffix} \
  --region ap-northeast-2 \
  --create-bucket-configuration LocationConstraint=ap-northeast-2

# 퍼블릭 액세스 차단 (보안 필수)
aws s3api put-public-access-block \
  --bucket dereel-data-{your-unique-suffix} \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,\
     BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Lifecycle 정책 — 5년 초과 데이터 자동 삭제
aws s3api put-bucket-lifecycle-configuration \
  --bucket dereel-data-{your-unique-suffix} \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "delete-old-data",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "Expiration": {"Days": 1825}
    }]
  }'
```

### 3.5 AWS Budget Alert 설정

```bash
# 월 $5 초과 시 이메일 경고 (NFR 비용 정책)
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget '{
    "BudgetName": "dereel-monthly-budget",
    "BudgetLimit": {"Amount": "5", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[{
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 100
    },
    "Subscribers": [{
      "SubscriptionType": "EMAIL",
      "Address": "your-email@example.com"
    }]
  }]'
```

---

## 4. 롤백 절차

### 4.1 Phase 1 — 코드 롤백

```bash
# 방법 1: 이전 커밋으로 revert
git revert HEAD
git push origin main

# 방법 2: 특정 커밋으로 reset (강제 push — 주의)
git log --oneline -10          # 롤백할 커밋 해시 확인
git reset --hard {commit-hash}
git push origin main --force-with-lease
```

### 4.2 Phase 1 — 상태 파일 롤백

크롤링 상태 파일(`data/*.json`)이 잘못 업데이트된 경우:

```bash
# 특정 파일만 이전 커밋으로 복원
git log --oneline data/stock_state.json    # 이력 확인
git checkout {commit-hash} -- data/stock_state.json
git commit -m "fix: stock_state.json 롤백 [skip ci]"
git push origin main
```

### 4.3 Phase 2 — DynamoDB 데이터 롤백

```bash
# 특정 아이템 삭제 (잘못 저장된 경우)
aws dynamodb delete-item \
  --table-name dereel-price-history \
  --key '{"PK": {"S": "steam:1245620"}, "SK": {"S": "raw#2026-04-13T10:00:00Z"}}' \
  --region ap-northeast-2
```

> DynamoDB는 Point-in-Time Recovery(PITR)를 활성화하면  
> 35일 이내 특정 시점으로 테이블 전체를 복원할 수 있다.
>
> ```bash
> # PITR 활성화 (Phase 2 배포 시 1회 실행)
> aws dynamodb update-continuous-backups \
>   --table-name dereel-price-history \
>   --point-in-time-recovery-specification \
>     PointInTimeRecoveryEnabled=true
> ```

---

## 5. 환경별 설정 관리

### 5.1 로컬 개발 환경

```bash
# .env 파일로 환경변수 관리
DEREEL_LOG_LEVEL=DEBUG          # 로컬에서는 DEBUG 레벨
DEREEL_DATA_DIR=./data
```

### 5.2 GitHub Actions (운영 환경)

```bash
# GitHub Secrets → 환경변수로 자동 주입
# .github/workflows/*.yml 에서 env: 섹션으로 매핑
DEREEL_LOG_LEVEL=INFO           # 운영에서는 INFO 레벨
```

### 5.3 환경 구분 전략

```
로컬 개발:   .env 파일 + --dry-run 플래그
운영 (CI):   GitHub Secrets + 실제 발송
```

Phase 2 이후 스테이징 환경이 필요한 경우:
- DynamoDB 테이블명에 `-staging` 접미사 추가
- S3 버킷을 별도 생성
- GitHub Environment(`staging`, `production`) 기능 활용

---

## 6. 배포 이후 모니터링

### 6.1 Phase 1 — GitHub Actions 로그

```
GitHub → Actions 탭
→ 워크플로 실행 목록에서 최근 실행 선택
→ 각 Step 로그 확인

주요 확인 포인트:
  ✅ "Install dependencies" — 의존성 설치 성공
  ✅ "Run stock/price crawler" — 오류 없이 완료
  ✅ "Commit state changes" — 상태 파일 커밋 성공
```

### 6.2 실패 알림 수신

GitHub Actions 실패 시 **가입된 GitHub 계정 이메일**로 자동 알림이 발송된다.

```
GitHub → Settings → Notifications
→ "Actions" 섹션
→ "Send notifications for failed workflows only" 체크 권장
```

### 6.3 Phase 2 — CloudWatch 메트릭

```bash
# Lambda 실행 오류 확인
aws logs filter-log-events \
  --log-group-name /aws/lambda/dereel-crawler \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s000) \
  --region ap-northeast-2
```

---

## 7. 배포 체크리스트 요약

### Phase 1-A 최초 배포

```
□ repo Public 여부 확인
□ GitHub Secrets 2개 등록 (BOT_TOKEN, CHAT_ID)
□ targets.yaml에서 apple_refurb enabled: true
□ 워크플로 파일 3개 존재 확인
□ workflow_dispatch로 수동 실행 → Actions 로그 성공 확인
□ data/stock_state.json 자동 커밋 확인
□ 두 번째 실행 후 Telegram 알림 수신 확인
```

### Phase 2-A 인프라 배포

```
□ AWS CLI 설치 및 configure 완료
□ IAM 사용자 생성 + 최소 권한 정책 적용
□ Access Key → GitHub Secrets 등록
□ DynamoDB 테이블 생성 + TTL 활성화
□ S3 버킷 생성 + 퍼블릭 액세스 차단
□ S3 Lifecycle 정책 (5년 자동 삭제) 설정
□ Budget Alert $5 설정
□ PITR 활성화
□ 워크플로에서 AWS SDK 연동 확인
```

---

## 8. 변경 이력

| 버전 | 날짜 | 내용 | 작성자 |
|---|---|---|---|
| v0.1.0 | 2026-04-13 | 최초 초안 작성 | 한섭 |
