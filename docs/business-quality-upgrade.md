# Business Quality Upgrade

- Generated: `2026-04-14T04:48:11.525239+00:00`
- Portfolio verdict: `충분`
- Business value score: `79.2`
- Upgrade phase: P1 도메인 범위 정리
- Primary motion: `intelligence`
- Weakest dimension: `operational_depth`

## Current Evidence

- Primary rows: `1805`
- Today raw rows: `27`
- Latest report items: `15`
- Match rate: `100.0%`
- Collection errors: `0`
- Freshness gap: `0`

## Upgrade Actions

- coffee split 후보는 mobility 운영 점수와 병합하지 않고 별도 domain_scope로 유지한다.
- EV 등록, 충전 요금, 대중교통 fare/payment policy source를 운영 레이어 후보로 보강한다.
- station/charger id canonical key와 availability snapshot freshness를 리포트 점검 항목으로 유지한다.

## Quality Contracts

- `config/categories/mobility.yaml`: output `reports/mobility_quality.json`, tracked `station_availability_snapshot, charger_availability_snapshot, transport_service_notice, fare_payment_policy_change`, backlog items `4`
- `config/categories/coffee.yaml`: output `-`, tracked `-`, backlog items `1`

## Contract Gaps

- None.
