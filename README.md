# MobilityRadar

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

대중교통, 교통 혼잡, 공유 모빌리티, 전기차 등 이동/교통 관련 뉴스를 자동 수집하고 경로 인사이트를 제공하는 레이더 프로젝트입니다.

## 프로젝트 목표

- **교통 동향 추적**: 대중교통, 혼잡도, 사고, 기상 영향 등 이동 관련 뉴스를 일일 자동 수집
- **모빌리티 트렌드 분석**: 공유 이동(Uber, 카카오택시), 마이크로 모빌리티(킥보드, 자전거), 전기차 동향 모니터링
- **경로 인사이트 제공**: MCP `route_suggest` 도구로 교통 관련 뉴스에서 경로 인사이트 자동 추출
- **혼잡 신호 감지**: 정체, 사고, 우회로 등 교통 상황 관련 뉴스 실시간 필터링
- **AI 교통 도우미**: MCP 서버를 통해 AI 어시스턴트에서 교통/이동 정보를 자연어로 검색

## 주요 기능

1. **RSS 자동 수집**: TechCrunch, The Verge, CityLab 등에서 모빌리티 관련 기사 수집
2. **엔티티 매칭**: 대중교통, 혼잡/교통, 공유 이동, 마이크로 모빌리티, 전기차 5개 카테고리
3. **DuckDB 저장**: UPSERT 시맨틱 기반 기사 저장
4. **JSONL 원본 보존**: `data/raw/YYYY-MM-DD/{source}.jsonl`
5. **SQLite FTS5 검색**: 전문검색으로 교통 뉴스 빠르게 검색
6. **자연어 쿼리**: "최근 1주 전기차 충전소 관련" 같은 자연어 검색
7. **HTML 리포트**: 카테고리별 통계가 포함된 자동 리포트
8. **MCP 서버**: search, recent_updates, sql, top_trends, route_suggest

## 빠른 시작

```bash
pip install -r requirements.txt
python main.py --category mobility --recent-days 7
```

- 리포트: `reports/mobility_report.html`
- DB: `data/radar_data.duckdb`

## 프로젝트 구조

```
MobilityRadar/
├── mobilityradar/
│   ├── collector.py       # RSS 수집
│   ├── analyzer.py        # 엔티티 키워드 매칭
│   ├── storage.py         # DuckDB 스토리지
│   ├── reporter.py        # HTML 리포트
│   ├── raw_logger.py      # JSONL 원본 기록
│   ├── search_index.py    # SQLite FTS5
│   ├── nl_query.py        # 자연어 쿼리 파서
│   └── mcp_server/        # MCP 서버 (5개 도구)
├── config/categories/mobility.yaml
├── tests/
├── .github/workflows/
└── main.py
```

## MCP 서버 도구

| 도구 | 설명 |
|------|------|
| `search` | FTS5 기반 자연어 검색 |
| `recent_updates` | 최근 수집 기사 조회 |
| `sql` | 읽기 전용 SQL 쿼리 |
| `top_trends` | 엔티티 언급 빈도 트렌드 |
| `route_suggest` | 교통 관련 경로 인사이트 |

## 테스트

```bash
pytest tests/ -v
```

## CI/CD

- `.github/workflows/radar-crawler.yml`: 매일 00:00 UTC 자동 수집
- GitHub Pages로 리포트 자동 배포
