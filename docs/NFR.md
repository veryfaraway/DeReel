# NFR (Non-Functional Requirements)
# DeReel — 비기능 요구사항 명세서

> **버전:** v0.1.0
> **작성일:** 2026-03-30
> **작성자:** 한섭
> **연관 문서:** [PRD.md](./PRD.md) | [FEATURES.md](./FEATURES.md)

---

## 1. 성능 (Performance)

### 1.1 크롤링 응답 처리
| 항목 | 기준값 | 비고 |
|---|---|---|
| 단일 크롤러 실행 시간 | 30초 이내 | 타임아웃 초과 시 실패 처리 |
| HTTP 요청 타임아웃 | 30초 | 재시도 1회 후 포기 |
| GitHub Actions 워크플로 총 실행 시간 | 5분 이내 | 초과 시 최적화 검토 |
| Telegram 알림 발송 지연 | 감지 후 1분 이내 | |

### 1.2 데이터 처리
| 항목 | 기준값 |
|---|---|
| 가격 이력 단건 저장 응답 시간 | 1초 이내 |
| 월별/연별 집계 배치 작업 완료 시간 | 10분 이내 |
| 감시 제품 수 최대 한도 (Phase 1) | 100개 이내 |

---

## 2. 비용 (Cost)

### 2.1 Phase별 비용 한도
| Phase | 월 목표 비용 | 핵심 전략 |
|---|---|---|
| **Phase 1** | $0 | GitHub Actions 공개 repo + Telegram Bot 무료 |
| **Phase 2** | $10 이하 | AWS Free Tier (Lambda, DynamoDB, S3) 범위 내 운영 |
| **Phase 3** | $50 이하 | Lightsail EC2 Kafka 자체 설치, MSK 미사용 |

### 2.2 비용 초과 방지 규칙
- AWS 리소스 생성 전 **비용 계산기로 사전 검토** 필수
- AWS Budget Alert 설정: 월 $5 초과 시 이메일 경고
- DynamoDB: On-Demand 모드 사용 (예측 불가한 트래픽 대비)
- S3: Lifecycle 정책으로 5년 초과 데이터 자동 삭제 (F-14 보관 정책 연동)
- GitHub Actions: 공개 repo 유지 (비공개 전환 시 월 2,000분 한도 주의)

---

## 3. 안정성 (Reliability)

### 3.1 장애 격리
- 단일 크롤러 실패가 **다른 크롤러 실행에 영향을 주지 않아야 함**
- 각 크롤러는 독립적인 try/except 블록으로 감싸고 실패 시 로그만 기록
- 알림 발송 실패는 크롤링 결과에 영향 없음 (알림과 크롤링 로직 분리)

### 3.2 재시도 정책
| 오류 유형 | 재시도 여부 | 재시도 횟수 | 대기 시간 |
|---|---|---|---|
| HTTP 타임아웃 | ✅ | 1회 | 10초 후 |
| HTTP 429 (Rate Limit) | ✅ | 1회 | 60분 후 (다음 실행 주기 위임) |
| HTTP 5xx (서버 오류) | ✅ | 1회 | 30초 후 |
| HTTP 4xx (클라이언트 오류) | ❌ | 없음 | 로그 기록 후 스킵 |
| 파싱 오류 (구조 변경) | ❌ | 없음 | 로그 기록 후 스킵 |
| Telegram 발송 실패 | ❌ | 없음 | 로그 기록 후 스킵 |

### 3.3 데이터 안전성
- 크롤링 결과가 비어있을 경우 이전 데이터를 덮어쓰지 않음 (오탐 방지)
- 알림 이력 저장 실패 시 알림 발송 스킵 (중복 발송보다 미발송 우선)
- 집계 배치 실패 시 원본 raw 데이터 보존 (집계 완료 후 원본 삭제)

---

## 4. 확장성 (Scalability)

### 4.1 크롤러 확장
- 새 크롤러 추가 시 **기존 코드 수정 없이** `crawlers/` 디렉토리에 파일 추가만으로 동작
- `BaseCrawler` 추상 클래스 인터페이스(`fetch` / `parse` / `format_message`) 구현 강제
- `targets.yaml`에 새 사이트 섹션 추가 시 자동 인식

### 4.2 감시 제품 수 확장
| Phase | 최대 제품 수 | 저장소 |
|---|---|---|
| Phase 1 | 100개 | GitHub repo JSON |
| Phase 2 | 1,000개 | AWS DynamoDB |
| Phase 3 | 무제한 | Kafka + S3 Parquet |

### 4.3 멀티유저 대비 설계 원칙
- Phase 1~2는 단일 사용자 전용이나, 향후 멀티유저 전환을 고려해 **사용자 식별자(user_id)를 데이터 구조에 예약 필드로 포함**
- 비즈니스 로직에서 user_id 하드코딩 금지 (환경변수 또는 설정값으로 주입)

---

## 5. 보안 (Security)

### 5.1 민감 정보 관리
| 항목 | 관리 방법 | 절대 금지 |
|---|---|---|
| Telegram Bot Token | GitHub Secrets | 코드 직접 작성, repo 커밋 |
| Telegram Chat ID | GitHub Secrets | 코드 직접 작성, repo 커밋 |
| 쿠팡 파트너스 Access Key | GitHub Secrets | 코드 직접 작성, repo 커밋 |
| 쿠팡 파트너스 Secret Key | GitHub Secrets | 코드 직접 작성, repo 커밋 |
| AWS Access Key ID | GitHub Secrets | 코드 직접 작성, repo 커밋 |
| AWS Secret Access Key | GitHub Secrets | 코드 직접 작성, repo 커밋 |

### 5.2 코드 보안 규칙
- `.env` 파일은 반드시 `.gitignore`에 등록
- 로그 출력 시 API 키, 토큰, 개인정보 마스킹 처리
- 공개 repo이므로 GitHub Secret Scanning 활성화 권장
- 의존성 취약점 점검: `pip audit` 또는 GitHub Dependabot 활성화

### 5.3 크롤링 윤리 보안
- 수집 대상 서버에 인증 우회 또는 비정상 접근 시도 금지
- 로그인이 필요한 페이지 접근 금지 (Out of Scope)
- 수집 데이터를 제3자에게 무단 제공 또는 판매 금지

---

## 6. 유지보수성 (Maintainability)

### 6.1 코드 품질 기준
| 항목 | 도구 | 기준 |
|---|---|---|
| 코드 포맷팅 | `black` | PEP 8 준수 |
| 린트 | `ruff` | 경고 0건 유지 |
| 타입 힌트 | `mypy` | 핵심 모듈 타입 힌트 필수 |
| 테스트 커버리지 | `pytest` | 핵심 로직 (감지, 알림, 집계) 80% 이상 |

### 6.2 로깅 규칙
| 레벨 | 사용 기준 |
|---|---|
| `INFO` | 크롤링 시작/완료, 알림 발송 성공, 집계 완료 |
| `WARNING` | 재시도 발생, 감시 제품 없음, 알림 중복으로 스킵 |
| `ERROR` | 크롤링 실패, 파싱 오류, 알림 발송 실패 |
| `DEBUG` | HTTP 요청/응답 원본 (로컬 개발 환경에서만 활성화) |

```python
# 로그 포맷 표준
[2026-03-30 18:00:00 KST] INFO  apple_refurb  | 크롤링 완료 (3개 제품 감지)
[2026-03-30 18:00:01 KST] INFO  notifier      | 알림 발송 성공 (AirPods Pro 2세대)
[2026-03-30 18:00:01 KST] WARNING notifier    | 알림 스킵 - 24시간 내 중복 (AirPods 4세대)
[2026-03-30 18:00:05 KST] ERROR apple_refurb  | HTTP 429 - 다음 주기에 재시도
```

### 6.3 문서 유지 원칙
- 기능 변경 시 관련 문서(`FEATURES.md`, `CHANGELOG.md`)를 **같은 PR에서 함께 수정**
- `targets.yaml` 구조 변경 시 `HOW_TO_ADD_CRAWLER.md` 동기화 필수

---

## 7. 법적/윤리적 준수 (Compliance)

### 7.1 사이트별 준수 사항
| 사이트 | robots.txt 확인 | 권장 주기 우선 적용 | 비고 |
|---|---|---|---|
| Apple | ✅ 매 실행 전 확인 | ✅ | 공개 JSON 엔드포인트 사용 |
| Steam | ✅ | ✅ | 공식 API Rate Limit 준수 |
| 쿠팡 | ✅ | ✅ | 파트너스 API ToS 준수 |
| GOG | ✅ | ✅ | 비공식 API 사용, 주기 보수적으로 설정 |
| Epic | ✅ | ✅ | HTML 파싱, User-Agent 브라우저 설정 |
| Amazon | ✅ | ✅ | 가장 보수적으로 운영, 최소 요청 |

### 7.2 공통 준수 규칙
- 모든 HTTP 요청에 실제 브라우저 `User-Agent` 헤더 설정
- 요청 간 최소 딜레이: `random.uniform(3.0, 8.0)` 초 적용
- `robots.txt` Disallow 경로 접근 금지
- 수집 데이터 상업적 재판매 금지 (개인 사용 및 오픈소스 교육 목적에 한정)

---

## 8. 관찰 가능성 (Observability)

### 8.1 Phase 1 (GitHub Actions 로그)
- 워크플로 실행 로그를 GitHub Actions 탭에서 확인
- 실패 시 GitHub 계정 이메일로 자동 알림

### 8.2 Phase 2 이후 (AWS CloudWatch)
- Lambda 실행 로그 → CloudWatch Logs 자동 수집
- 크롤링 성공/실패 메트릭 → CloudWatch Metrics 커스텀 지표 등록
- 연속 3회 크롤링 실패 시 → CloudWatch Alarm → Telegram 장애 알림

---

## 9. 변경 이력

| 버전 | 날짜 | 내용 | 작성자 |
|---|---|---|---|
| v0.1.0 | 2026-03-30 | 최초 초안 작성 | 한섭 |
