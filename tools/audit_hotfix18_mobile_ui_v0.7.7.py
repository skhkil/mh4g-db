#!/usr/bin/env python3
from pathlib import Path
import json,glob
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/'js/app.js').read_text(encoding='utf-8')
css=(ROOT/'css/app.css').read_text(encoding='utf-8')
index=(ROOT/'index.html').read_text(encoding='utf-8')
loader=(ROOT/'js/data-loader.js').read_text(encoding='utf-8')
checks={
 'version_index':'hotfix18' in index,
 'version_app':'hotfix18' in app.splitlines()[0] and 'hotfix18' in app.splitlines()[1] and 'hotfix18' in app,
 'version_loader':'hotfix18' in loader.splitlines()[0],
 'armor_detail_full_width_mobile':'#armorTable .data-table.responsive-table tbody tr.armor-detail-row' in css and 'grid-column:1/-1!important' in css,
 'armor_progress_two_columns_mobile':'.armor-progress-material-grid' in css and 'minmax(0,.95fr) minmax(0,1.05fr)' in css,
 'quest_filter_nav':'progressionQuestFilterButton' in app and 'type==="questfilter"' in app,
 'quest_filter_by_rank':'navLevel' in app and 'questLevelFilter' in app,
 'quest_filter_by_reward':'navReward' in app and 'rewardMatch' in app,
 'quest_filter_by_monster':'navMonster' in app and 'questMonsterFilter' in app,
}
malformed=0
quest_noid=0
for fn in glob.glob(str(ROOT/'data/armor_progressions/*.json')):
    p=json.loads(Path(fn).read_text(encoding='utf-8'))
    for m in p.get('materials',[]):
        for s in m.get('sources',[]):
            if s.get('type')=='event': malformed+=1
            if s.get('type')=='quest' and not s.get('id'): quest_noid+=1
checks['special_event_sources_normalized']=malformed==0
checks['noid_quest_sources_present_for_filtering']=quest_noid>0
out={'ok':all(checks.values()),'version':'0.7.7-chat4-research2-hotfix18','checks':checks,'stats':{'malformedEventSources':malformed,'noIdQuestSources':quest_noid}}
(ROOT/'tools/hotfix18_mobile_ui_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['ok'] else 1)
