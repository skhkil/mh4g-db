# Weapon tree runtime recovery report

## 문제점
무기 트리 추가본에서 HTML/CSS만 표시되고 메뉴와 버튼이 모두 무반응.

## 원인
`app.js` 동일 스코프에서 `openWeaponDetail`이 상태 변수와 함수명으로 중복 선언되어 브라우저 ES Module 파싱 단계에서 `Identifier 'openWeaponDetail' has already been declared` 오류 발생. 따라서 모듈 전체가 실행되지 않아 `bind()`가 호출되지 않음.

## 수정
- 상태 변수명을 `openWeaponDetailRow`로 변경.
- 무기 트리 인덱스/개별 참조 로딩을 초기 `data-loader.js` 의존성에서 분리.
- 무기 페이지/행 선택 시에만 lazy fetch.
- 트리 파일 로드 실패를 catch하여 전역 앱 초기화와 격리.

## 검증
- `node --check` app/data-loader 통과
- Chromium ES Module 파싱 및 평가: 오류 0건
- Chromium DOM smoke test: 스킬 메뉴 전환 정상, 무기 드롭다운 열기 정상
