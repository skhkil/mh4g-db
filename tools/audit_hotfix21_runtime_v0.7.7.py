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
 'index_runtime_version': '0.7.7-step4-final-release' in idx,
 'app_runtime_version': '0.7.7-step4-final-release' in app,
 'engine_profiles': all(x in eng for x in ['complex4','complex5','balanced3','timeBudgetMs','nearMisses']),
 'engine_yields': 'await yieldUi()' in eng and 'candidateIndex+1)%5' in eng,
 'near_miss_ui': all(x in app for x in ['renderNearMissCard','현재 조건에서 완성 조합을 찾지 못했습니다','pt 부족','고속 후보검색(완전탐색 아님)']),
 'condition_summary_ui': 'autoSearchConditionText' in app and '무기 슬롯' in app and '호석 슬롯' in app,
 'condition_hint_html': '자동조합은 진행도와 무기 슬롯을 기준으로 계산합니다.' in idx,
 'readme_hotfix21_recorded': '2026-09-30 hotfix21' in readme,
 'work_status_hotfix21_recorded': '2026-09-30 hotfix21' in status,
}
errors=[k for k,v in checks.items() if not v]
out={'ok':not errors,'version':'0.7.7-chat4-research2-hotfix21','checks':checks,'errors':errors}
(ROOT/'tools/hotfix21_runtime_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2));raise SystemExit(0 if out['ok'] else 1)
