#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'ui_rewards_hotfix3_release_gate_v0.7.7.json'
checks={}; errors=[]

def ok(name,val,detail=None):
    checks[name]=bool(val)
    if not val: errors.append(name if detail is None else f'{name}: {detail}')

# ES module syntax
for rel,name in [('js/app.js','app_module_syntax'),('js/data-loader.js','loader_module_syntax'),('js/engine.js','engine_module_syntax')]:
    r=subprocess.run(['node','--check',str(ROOT/rel)],capture_output=True,text=True)
    ok(name,r.returncode==0,r.stderr.strip()[:300])

app=(ROOT/'js/app.js').read_text(encoding='utf-8')
idx=(ROOT/'index.html').read_text(encoding='utf-8')
items=json.loads((ROOT/'data/items.json').read_text(encoding='utf-8'))
item_ids={x.get('id') for x in items}
item_by_id={x.get('id'):x for x in items}

ok('cache_key_index','0.7.7-chat4-ui-reward-hotfix3' in idx)
ok('cache_key_app',app.count('0.7.7-chat4-ui-reward-hotfix3')>=2)
ok('near_miss_apply','data-auto-near' in app and 'applyAutoNearMissToSimulator' in app)
ok('undefined_guard','validName' in app and 't!=="undefined"' in app)
ok('skill_sort_restore','skillRowRank' in app and 'localeCompare(skillName' in app)
ok('quest_target_matcher','function questTargetMonsters' in app and 'occupied=Array' in app)
ok('festival_duplicate_removed','item_web_a5107065c21e' not in item_ids)
fest=item_by_id.get('item_de1d9ce2dacc',{})
ok('festival_alias',fest.get('nameEn')=='Festival Drum Music' and 'Festival Drum Music' in (fest.get('aliases') or []))
ok('festival_ref_file',(ROOT/'data/item_refs/item_de1d9ce2dacc.json').exists())
ok('ecan_ref_file',(ROOT/'data/item_refs/item_ae0c44459ddc.json').exists())
if (ROOT/'data/item_refs/item_ae0c44459ddc.json').exists():
    ecan=json.loads((ROOT/'data/item_refs/item_ae0c44459ddc.json').read_text(encoding='utf-8'))
    ok('ecan_three_uses',len(ecan.get('uses') or [])==3)

# Structured reports that must be OK
reports={
 'hotfix3_e2e':'tools/hotfix3_quest_links_near_skill_e2e_v0.7.7.json',
 'event_reward_links':'tools/event_reward_entity_links_e2e_v0.7.7.json',
 'complex_search':'tools/hotfix21_complex_search_e2e_v0.7.7.json',
 'owned_charm_auto_weapon':'tools/auto_build_stage3_5_e2e_v0.7.7.json',
 'stability':'tools/hotfix17_stability_e2e_v0.7.7.json',
 'ui_rewards':'tools/ui_rewards_hotfix_e2e_v0.7.7.json',
 'auto_rank_smoke':'tools/hotfix20_auto_rank_smoke_e2e_v0.7.7.json',
 'stage1_threshold':'tools/auto_build_stage1_threshold_audit_v0.7.7.json',
 'stage2_resources':'tools/auto_build_stage2_resource_audit_v0.7.7.json',
 'stage4_6':'tools/auto_build_stage4_6_audit_v0.7.7.json',
}
for name,rel in reports.items():
    p=ROOT/rel
    if not p.exists(): ok(name,False,'missing'); continue
    try: d=json.loads(p.read_text(encoding='utf-8')); ok(name,d.get('ok') is True)
    except Exception as e: ok(name,False,str(e))

xref=json.loads((ROOT/'data/xref_audit_v0.7.7.json').read_text(encoding='utf-8'))
ok('xref_hard_zero',xref.get('hardIssueCount')==0,str(xref.get('issues')))

# Verify specific E2E facts explicitly
try:
    h=json.loads((ROOT/'tools/hotfix3_quest_links_near_skill_e2e_v0.7.7.json').read_text(encoding='utf-8'))['facts']
    ok('ruby_subspecies_only',h.get('ruby_monsters')==['바살모스 아종'])
    ok('spaced_monster_normalized','도스재기' in h.get('무리의 우두머리, 도스재기!',[]))
    ok('punct_monster_normalized','게넬·셀타스' in h.get('중량급의 여제',[]))
    ok('ecan_links_verified',len(h.get('ecan_uses',[]))==3)
    order=h.get('skill_status_order',[])
    first_pending=next((i for i,x in enumerate(order) if x.startswith('미발동')),len(order))
    ok('activated_before_pending',all(not x.startswith('미발동') for x in order[:first_pending]))
    ok('near_transfer_verified','방어력' in h.get('manual_after_near',''))
except Exception as e:
    ok('specific_e2e_facts',False,str(e))

report={'version':'0.7.7-chat4-ui-reward-hotfix3','ok':not errors,'checks':checks,'errors':errors}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(0 if report['ok'] else 1)
