#!/usr/bin/env python3
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
idx=(ROOT/'index.html').read_text(encoding='utf-8')
app=(ROOT/'js/app.js').read_text(encoding='utf-8')
eng=(ROOT/'js/engine.js').read_text(encoding='utf-8')
readme=(ROOT/'README.md').read_text(encoding='utf-8')
status=(ROOT/'WORK_STATUS_v0.7.7.md').read_text(encoding='utf-8')
checks={
 'index_hotfix21': '0.7.7-chat4-research2-hotfix21' in idx,
 'app_hotfix21': '0.7.7-chat4-research2-hotfix21' in app,
 'engine_profiles': all(x in eng for x in ['complex4','complex5','balanced3','timeBudgetMs','nearMisses']),
 'engine_yields': 'await yieldUi()' in eng and 'candidateIndex+1)%5' in eng,
 'near_miss_ui': all(x in app for x in ['renderNearMissCard','현재 조건에서 완성 조합을 찾지 못했습니다','pt 부족','고속 후보검색(완전탐색 아님)']),
 'condition_summary_ui': 'autoSearchConditionText' in app and '무기 슬롯' in app and '호석 슬롯' in app,
 'condition_hint_html': '자동조합은 현재 수동 시뮬레이터에서 선택한 무기 슬롯과 호석 스킬/슬롯 조건을 함께 사용합니다.' in idx,
 'readme_hotfix21_first': readme.lstrip().startswith('> **2026-09-30 hotfix21'),
 'work_status_hotfix21_first': status.lstrip().startswith('## 2026-09-30 hotfix21'),
}
errors=[k for k,v in checks.items() if not v]
out={'ok':not errors,'version':'0.7.7-chat4-research2-hotfix21','checks':checks,'errors':errors}
(ROOT/'tools/hotfix21_runtime_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2));raise SystemExit(0 if out['ok'] else 1)
