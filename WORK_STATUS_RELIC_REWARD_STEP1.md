# MH4G 발굴가이드 보상표 Step 1 (2026-10-15)

기준: mh4g-db-v0.7.7_monster_filter1.zip. 제외: chat4_research2_hotfix8(1).zip.

## 반영
- data/relic_equipment.json: qualityGuide.monsterRewardSlots 24종 (23종 단일 보상칸 확인, 디아블로스 단일 기본 범위 미확인) 및 2두 보상 주의사항.
- js/app.js: 발굴가이드 내 전체 몬스터 단일 보상칸 표 및 MH4G@wiki 링크.
- js/data-loader.js, index.html: 캐시 키 0.7.7-relic-reward-roster-step1.
- README.md 최상단 변경기록.

출처: https://w.atwiki.jp/3dsmh4g/pages/395.html
주의: 보상칸 수는 발굴 품질/감정품 획득 개수/위험도 등급과 별개. 극한화 변동 별도. 2두 보상칸은 단일 보상칸 단순 합산이 아님.

## 완료 검증
- node --check js/app.js, js/data-loader.js 성공.
- tools/e2e_relic_guide_v0.7.7.py: PC 1365 / 모바일 390 통과.
- tools/e2e_back_navigation_v0.7.7.py: 추천장비→시뮬레이터→뒤로 15회 통과.
- tools/e2e_auto_build_stage3_5_v0.7.7.py: 통과.

## 미완료 / 실패 아닌 미검증
- e2e_relic_sim_hotfix12_v0.7.7.py: 실행 제한시간 초과, 로그 없음. 코드/테스트 원인 분리 필요.
- node tools/step3b_optimizer_regression_v0.7.7.mjs: 실행 제한시간 초과.
- 신규 보상표에 대한 별도 브라우저 assertion 및 전체 자동조합↔수동 정합성.
- 우카우카우 필수 회귀, 발굴 전용 회귀, 최종 재압축해제.
- 단일 보상칸 표 외 품질군/2두 추천 파밍 조합 증거 조사.

**미완료 회귀로 최종 ZIP 생성하지 않음.**
