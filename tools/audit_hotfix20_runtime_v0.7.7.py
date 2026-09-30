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
 'index_app_hotfix20':'./js/app.js?v=0.7.7-chat4-research2-hotfix20' in idx,
 'index_css_hotfix20':'./css/app.css?v=0.7.7-chat4-research2-hotfix20' in idx,
 'app_imports_hotfix20':all('hotfix20' in x for x in app.splitlines()[:2]),
 'app_version_hotfix20':'const APP_VERSION="0.7.7-chat4-research2-hotfix20"' in app,
 'progression_ui':all(x in idx for x in ['id="autoProgressionRank"','value="low"','value="high"','value="g"']),
 'progression_filter_engine':'progressionRankAllows(a.rank,rank)' in eng,
 'target_final_validation':eng.count('targetRequirementsSatisfied(')>=3,
 'negative_rank_metrics':'negativeSkillBurden(calc)' in eng and 'negativeSkillSeverity' in eng,
 'decoration_rank_metrics':'usedDecorationSlots' in eng and 'distinctDecorationTypes' in eng,
 'waste_rank_metrics':'targetWastePoints' in eng and 'targetUpgradeSteps' in eng,
 'extra_skill_rank_metrics':'extraPositiveSkillCount' in eng,
 'practical_rank_metrics':all(x in eng for x in ['rankMaxDowngrade','rankTotalDowngrade','defense','remainingSlots']),
 'resistance_rank_metrics':all(x in eng for x in ['resistanceTotal','resistanceMinimum']),
 'stable_tie':'buildSignature(a.armors).localeCompare(buildSignature(b.armors))' in eng,
 'exact_tie_diversity':'diversifyExactTieGroups' in eng,
 'armor_picker_resistance':'DEF ${a.defense} · 내성 ${resistText(a.resistances)}' in app,
 'selected_armor_resistance':'class="loadout-resist"' in app and '.loadout-resist' in (ROOT/'css/app.css').read_text(encoding='utf-8'),
 'auto_card_resistance':'내성합 ${resistTotal' in app,
 'readme_top_hotfix20':readme.lstrip().startswith('> **2026-09-30 hotfix20'),
 'readme_hotfix19_order':readme.find('hotfix20')<readme.find('hotfix19')<readme.find('hotfix18'),
 'work_status_hotfix20':'자동조합 계층형 랭킹 / 내성 반영 (hotfix20)' in status,
}
out={'ok':all(checks.values()),'version':'0.7.7-chat4-research2-hotfix20','checks':checks}
(ROOT/'tools/hotfix20_runtime_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2));raise SystemExit(0 if out['ok'] else 1)
