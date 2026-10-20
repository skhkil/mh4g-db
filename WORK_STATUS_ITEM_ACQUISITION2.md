# 소재 획득 조건 정정 — v0.7.7-item-acquisition2

- 기준본: `mh4g-db-v0.7.7_item_acquisition1.zip`
- 대상: `공폭룡 강고리발톱`의 광폭 이블조 42%, 이블조 36%, 극한 이블조 32% 기록.
- 원인: 원본 `method`가 `최대 3회`로 잘못 저장되어 유실물 유형이 화면에서 사라짐. 앱은 `data/item_refs/` 개별 레코드를 로드함.
- 정정: 유실물 / 최대 3회 / 포식 시 또는 구속공격 종료 시. 통합 및 개별 레코드 모두 수정.
- 극한 표시는 `G급 · 극한상태`로 변경. 다른 불명확한 기록은 자동 변환하지 않음.
- 출처: https://w.atwiki.jp/3dsmh4g/pages/285.html ; https://w.atwiki.jp/3dsmh4g/pages/287.html
- 회귀: item_acquisition2 E2E PC 1365/모바일 390, 발굴가이드 PC/모바일, 뒤로가기 15회, 자동→수동 계산 4건, optimizer3 우카우카우, JS 구문 검사 모두 통과.
- 캐시 키: `0.7.7-item-acquisition2`.
- 향후 과제: 다른 `최대 N회` 원본 획득방식에 대한 MH4G 자료별 전수 대조.
