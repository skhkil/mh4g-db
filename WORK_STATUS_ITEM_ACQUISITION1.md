# 소재 획득 UI 개선 — 2026-10-20

- 기준: mh4g-db-v0.7.7_relic_reward_final1.zip
- 캐시: `0.7.7-item-acquisition1`
- 수정: `js/app.js`, `css/app.css`, `index.html`, `js/data-loader.js`, `README.md`
- 몬스터 소재 획득 원본 4,481건의 `method`, `count`, `probability` 표시를 런타임에서 의미별로 구분. 원본 JSON 값은 변경하지 않음.
- `최대 N회`는 확인되지 않은 종류의 획득 기회로 표시; 본체 갈무리라고 추정하지 않음. `N회`가 별도 `count`에 저장된 경우 원본 횟수로 표시.
- 확률은 원본 기록의 표기이며, 여러 번 시도할 때의 누적 획득 확률로 계산하지 않음. 포맷이 잘못된 확률은 원본과 경고 유지.
- E2E: tools/e2e_item_acquisition1.py PC 1365px / 모바일 390px 모두 통과.
- 회귀: tools/e2e_back_navigation_v0.7.7.py (15회), tools/e2e_relic_guide_v0.7.7.py, tools/e2e_relic_sim_hotfix12_v0.7.7.py, tools/e2e_step3_auto_manual_parity_v0.7.7.py, tools/step3b_optimizer_regression_v0.7.7.mjs 모두 정상 종료 0.
- 미해결 데이터 정확성 이슈: 원본 `최대 N회` 항목의 실제 방법은 외부 자료 전수검증 전까지 미확인. 단순 UI 명확화와 원본 데이터 교정은 구별.
