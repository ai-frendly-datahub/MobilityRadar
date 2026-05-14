# MOBILITYRADAR

CityBikes API와 모빌리티 관련 뉴스를 수집하여 공유 모빌리티 서비스의 가용성과 트렌드를 분석합니다.

## STRUCTURE

```
MobilityRadar/
├── mobilityradar/
│   ├── collector.py              # collect_sources() — CityBikes API 및 모빌리티 뉴스
│   ├── analyzer.py               # apply_entity_rules() — 모빌리티 유형별 키워드 매칭 (자전거, 킥보드, 스쿠터 등)
│   ├── reporter.py               # generate_report() — Jinja2 HTML
│   ├── storage.py                # RadarStorage — DuckDB upsert/query/retention
│   ├── models.py                 # Source, Article, EntityDefinition, CategoryConfig
│   ├── config_loader.py          # YAML 로딩
│   ├── logger.py                 # structlog 구조화 로깅
│   ├── notifier.py               # Email/Webhook 알림
│   ├── raw_logger.py             # JSONL 원시 로깅
│   ├── search_index.py           # SQLite FTS5 전문 검색
│   ├── nl_query.py               # 자연어 쿼리 파서
│   ├── common/                   # 공유 유틸리티
│   └── mcp_server/               # MCP 서버 (server.py + tools.py)
├── config/
│   ├── config.yaml               # database_path, report_dir, raw_data_dir, search_db_path
│   └── categories/mobility.yaml  # 소스 + 엔티티 정의
├── data/                         # DuckDB, search_index.db, raw/ JSONL
├── reports/                      # 생성된 HTML 리포트
├── tests/unit/                   # pytest 단위 테스트
├── main.py                       # CLI 엔트리포인트
└── .github/workflows/radar-crawler.yml
```

## ENTITIES

| Entity | Examples |
|--------|----------|
| VehicleType | EV, e-scooter, ebike, 자율주행 |
| Service | Lime, Bird, Uber, 공유자전거 |
| ChargingInfra | 충전소, charger, supercharger |
| Regulation | safety, helmet, speed limit, 규제 |

## DEVIATIONS FROM TEMPLATE

- EV, 마이크로모빌리티, 공유 이동 서비스, 교통 정책 source를 함께 추적한다.
- 공공 교통/충전 인프라 JavaScript source는 selector 안정성 확인 전 확대하지 않는다.
- 차량·서비스·규제·충전 인프라 엔티티를 분리해 리포트한다.

## COMMANDS

```bash
python main.py --category mobility --recent-days 7
python main.py --category mobility --per-source-limit 50 --keep-days 90
```
