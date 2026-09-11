# MH4G DB 수집 / 정규화 도구 v0.4

## Windows 원클릭
`update_db.bat`을 더블클릭합니다.

수행 순서:
1. Python 의존성 설치
2. `crawl_source.py`: 원본 `/mh4g/` 내부 페이지 수집
3. `extract_tables.py`: 구형 HTML table의 rowspan/colspan 정리
4. `build_database.py --publish`: 실제 DB 정규화 + 검증 + 프로젝트 `data/` 반영
5. 분석용 `MH4G_DB_analysis.zip` 생성

## 생성되는 실제 DB
```text
data/
├─ armors.json
├─ decorations.json
├─ skills.json
├─ weapons.json
├─ items.json
└─ meta.json
```

## 중간/검증 데이터
```text
tools/
├─ raw_html/
├─ crawl_manifest.json
├─ raw_tables.json
└─ generated/
   ├─ report.json
   └─ data/
```

`build_database.py --publish`는 최소 데이터 개수, 미매핑 스킬, 해석 불가 스킬 셀 등을 검사합니다. 검증에 실패하면 프로젝트 `data/`를 덮어쓰지 않습니다.

## 인코딩
구형 원본 사이트의 한국어 페이지는 CP949/EUC-KR 계열입니다. v0.2에서 `requests`가 ISO-8859-1로 잘못 추정할 수 있었던 문제를 v0.4에서 수정하여 META charset 및 CP949를 우선합니다.

이미 v0.2 방식으로 수집되어 `ÇÏÀ§`처럼 깨진 `raw_tables.json`도 `build_database.py`가 CP949 mojibake를 복구할 수 있습니다.

## v0.4 무기 파생 / 예리도
`build_database.py`는 무기 페이지의 `~ 파생계` 제목과 트리 기호(├, └, │, ■)를 보존합니다.

근접무기는 원본 표의 `예리도` / `예리도+1` 게이지 문자열을 분석하여 `sharpness` 필드를 생성합니다. 각 레코드에는 `confidence`가 포함되며 원본에서 게이지 자체를 읽을 수 없는 경우 임의의 게이지를 생성하지 않습니다.


## 방어구 등급 판정
`build_database.py`는 방어구의 `rank`를 단순 RARE 구간이 아니라 **최초 제작 가능 진행도**로 계산합니다.
RARE4는 하위/상위가 혼재하므로 S 계열 여부, 원본 소재 입수 등급, 확인된 하위 예외를 조합해 판정합니다.
재생성 시에도 같은 규칙이 적용됩니다.
