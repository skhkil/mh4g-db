# 발굴 방어구 혼합 조합 최종 패키지 — 2026-10-27

## 구현
- 발굴 방어구 보유 목록을 브라우저 localStorage에 독립 저장
- 부위, 검사·거너, 방어력, 5속성 내성, 고정 스킬 포인트, 실제 사용 가능한 빈 슬롯 입력
- 수동조합 부위별 제작/발굴 전환, 보유 발굴 방어구 행 클릭 적용 및 삭제
- 자동조합 `보유 발굴방어구 사용` 옵션을 통한 발굴 후보 포함
- 몸통배가, 장식주 사용 등 기존 계산 옵션 유지

## 실행한 검증
- `node --check js/app.js` — 통과
- `node --check js/engine.js` — 통과
- `node tools/relic_armor_mixed_regression.mjs` — 통과 (혼합 방어력·내성·고정 스킬 합산과 자동조합 후보 탐색)
- `node tools/step3b_optimizer_regression_v0.7.7.mjs` — 통과 (기존 우카우카우 및 자동조합 회귀 테스트)

## 테스트 제한
- Playwright + Chromium을 사용한 E2E 시도는 브라우저에서 localhost와 file URL 모두 `net::ERR_BLOCKED_BY_ADMINISTRATOR`로 차단되어 수행하지 못함.
- 따라서 PC·모바일 실제 화면 클릭, 로컬 저장 후 새로고침 복원은 별도 브라우저 실사용 검증이 필요함.
- GitHub 원격 사이트에 직접 배포하거나 라이브 사이트를 변경하지 않았음.
