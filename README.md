# MobilityRadar

혼잡/이동(모빌리티) 관련 뉴스를 수집하고, 엔티티를 분석해 DuckDB에 저장한 뒤 HTML 리포트를
생성하는 Radar 프로젝트입니다.

## Quick Start
1. 의존성 설치
   ```bash
   pip install -r requirements.txt
   ```
2. 실행
   ```bash
   python main.py --category mobility --recent-days 7
   ```
3. 결과 확인
   - 리포트: `reports/mobility_report.html`
   - DB: `data/radar_data.duckdb`

## Mobility Category
- 카테고리 파일: `config/categories/mobility.yaml`
- 트래킹 범위:
  - 대중교통 도착/운행 관련 이슈
  - 혼잡/정체 및 교통 상황
  - 공유 이동 서비스
  - 마이크로 모빌리티
  - 전기차/충전 인프라

## MCP Server
- 서버 이름: `mobilityradar`
- 주요 툴:
  - `search`
  - `recent_updates`
  - `sql`
  - `top_trends`
  - `route_suggest` (최근 모빌리티 기사 기반 경로/혼잡 인사이트 요약)

## GitHub Actions
- 워크플로: `.github/workflows/radar-crawler.yml`
- 이름: `MobilityRadar Crawler`
- 기본 카테고리: `RADAR_CATEGORY=mobility`
