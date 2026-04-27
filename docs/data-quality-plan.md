# Data Quality Plan

- 생성 시각: `2026-04-23T14:45:24.863320+00:00`
- 우선순위: `P1`
- 데이터 품질 점수: `73`
- 가장 약한 축: `운영 깊이`
- Governance: `medium`
- Primary Motion: `intelligence`

## 현재 이슈

- 가장 약한 품질 축은 운영 깊이(45)

## 필수 신호

- EV 등록·충전소·충전 요금 같은 운영 지표
- 대중교통 요금·노선·운행 상태
- mobility/coffee domain_scope 기반의 split 후보 관리

## 품질 게이트

- 도메인 tag를 mobility/coffee로 명시해 혼합 집계를 방지
- 지역·정류장·충전소 식별자를 canonical key로 유지
- 요금·가동상태·수집일을 분리하고 stale 상태를 표시

## 다음 구현 순서

- coffee split 후보를 별도 repo로 승격할지 결정
- EV 등록·충전 요금·대중교통 요금 source를 운영 레이어로 추가
- 지역별 mobility score 산출 시 공식/운영/시장 레이어를 따로 표시

## 운영 규칙

- 원문 URL, 수집일, 이벤트 발생일은 별도 필드로 유지한다.
- 공식 source와 커뮤니티/시장 source를 같은 신뢰 등급으로 병합하지 않는다.
- collector가 인증키나 네트워크 제한으로 skip되면 실패를 숨기지 말고 skip 사유를 기록한다.
- 이 문서는 `scripts/build_data_quality_review.py --write-repo-plans`로 재생성한다.
