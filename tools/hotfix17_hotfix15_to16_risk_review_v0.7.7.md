# hotfix15 → hotfix16 runtime risk review

- `js/app.js`: 전체 방어구 제작 진행 지연 로딩, 방어구 행 전체 클릭/키보드 토글, 상세행 렌더링이 추가됨. `loadArmorProgression()` await 경로를 `try/catch/finally`로 격리해 개별 JSON 실패가 document 이벤트 체인으로 전파되지 않게 수정.
- `js/data-loader.js`: `loadArmorProgression()` 추가. 기본 앱 초기화와 분리된 개별 fetch로 유지.
- `css/app.css`: 상세행/가로형 제작 진행 UI 추가. 런타임 코드 영향 없음.
- `index.html`: hotfix16 캐시 키 변경만 존재. hotfix17에서 전체 캐시 키 동기화.
- 기존 공통 취약점: `bind()` 시작 시 `appEventsBound=true`가 먼저 설정되어 중간 예외 발생 시 재바인딩 불가. hotfix17에서 그룹별 바인딩 + 성공 후 완료 처리로 제거.
- 렌더링 위험: hotfix16은 방어구 1건당 기본행+상세행 2개를 생성해 전체 결과에서 DOM이 급증. hotfix17에서 180개 단위 단계 렌더링으로 제한.

검토 결론: hotfix16 기능 자체는 유지하되 비동기 오류 전파, 전역 바인딩 완료 플래그, 대량 DOM 생성 세 지점을 런타임 위험 요소로 분류하고 hotfix17에서 차단함.
