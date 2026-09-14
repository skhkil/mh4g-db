#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
import sqlite3
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

TYPE_MAP = {
    "대검":"Great Sword","태도":"Long Sword","한손검":"Sword and Shield","쌍검":"Dual Blades",
    "해머":"Hammer","수렵피리":"Hunting Horn","랜스":"Lance","건랜스":"Gunlance",
    "슬래시액스":"Switch Axe","차지액스":"Charge Blade","조충곤":"Insect Glaive",
    "라이트보우건":"Light Bowgun","헤비보우건":"Heavy Bowgun","활":"Bow",
}

MIXED_WEAPON_PRIMARY = {
    "weapon_4a29d9b2bfee": ("왕아노【야뢰】", "王牙弩【野雷】"),
    "weapon_0900425cc680": ("봉룡검【절일문】", "封龍剣【絶一門】"),
    "weapon_a09c69551f05": ("봉룡검【원절일문】", "封龍剣【怨絶一門】"),
    "weapon_172a639ba74a": ("파룡검【사절일문】", "破龍剣【邪絶一門】"),
    "weapon_c794cee0f43b": ("봉룡검【초절일문】", "封龍剣【超絶一門】"),
    "weapon_65fe5731363d": ("봉룡검【진절일문】", "封龍剣【真絶一門】"),
    "weapon_ad82de641bdc": ("봉룡검【극절일문】", "封龍剣【極絶一門】"),
}

def norm(text: str | None) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text or ""))

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def dump_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def load_verified_weapon_aliases(project: Path) -> dict[str, str]:
    script = project / "tools" / "merge_mh4u_sharpness.py"
    module = ast.parse(script.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "VERIFIED_ALIASES" for t in node.targets):
            return ast.literal_eval(node.value)
    return {}

def unique_index(rows, key):
    idx = defaultdict(list)
    for row in rows:
        k = key(row)
        if k:
            idx[k].append(row)
    return idx

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--mh4u", required=True)
    ap.add_argument("--athena")
    args = ap.parse_args()

    root = Path(args.project)
    data_dir = root / "data"
    con = sqlite3.connect(args.mh4u)
    con.row_factory = sqlite3.Row

    db_items = [dict(r) for r in con.execute(
        "select _id,name,name_jp,type,sub_type,rarity from items where name_jp is not null and name_jp<>''"
    )]
    item_jp = unique_index(db_items, lambda r: norm(r.get("name_jp")))

    db_weapons = [dict(r) for r in con.execute(
        "select w._id,w.wtype,w.attack,w.affinity,w.num_slots,i.name,i.name_jp from weapons w join items i on i._id=w._id"
    )]
    weapon_jp = unique_index(db_weapons, lambda r: (norm(r.get("name_jp")), r.get("wtype")))
    weapon_en = {r["name"]: r for r in db_weapons}
    aliases = load_verified_weapon_aliases(root)

    db_trees = [dict(r) for r in con.execute("select _id,name,name_jp from skill_trees")]
    tree_jp = unique_index(db_trees, lambda r: norm(r.get("name_jp")))
    db_skills = [dict(r) for r in con.execute(
        "select _id,skill_tree_id,required_skill_tree_points,name,name_jp from skills"
    )]
    skills_by_tree_points = unique_index(db_skills, lambda r: (int(r["skill_tree_id"]), int(r["required_skill_tree_points"])))

    report = {
        "version": "0.7.6",
        "policy": {
            "primary": "Korean is canonical. Seven legacy weapon names that contained Korean + trailing Japanese in one field are split into Korean name + Japanese nameJa without changing the Korean wording.",
            "secondary": ["Japanese", "English"],
            "matching": "Exact normalized Japanese match only, plus the 26 weapon aliases already verified in v0.7.5. Skill activation English uses exact parent skill-tree mapping + activation points.",
            "guessing": "No new fuzzy/heuristic name matches are written."
        },
        "source": ["user-supplied MonsterHunter4UDatabase mh4u.db", "existing v0.7.5 verified weapon aliases"],
        "summary": {},
        "unresolved": {},
    }

    # Normalize seven legacy mixed-language weapon names: keep Korean in name, move/correct Japanese to nameJa.
    normalized_mixed = []
    wp = data_dir / "weapons.json"
    weapon_rows = load_json(wp)
    for w in weapon_rows:
        target = MIXED_WEAPON_PRIMARY.get(w.get("id"))
        if not target:
            continue
        ko, ja = target
        before = {"name": w.get("name", ""), "nameJa": w.get("nameJa", "")}
        w["name"] = ko
        w["nameJa"] = ja
        normalized_mixed.append({"id":w.get("id"),"before":before,"after":{"name":ko,"nameJa":ja}})
    dump_json(wp, weapon_rows)
    sp = data_dir / "sim_weapons.json"
    sim_rows = load_json(sp)
    full_by_id = {w["id"]: w for w in weapon_rows}
    for r in sim_rows:
        full = full_by_id.get(r.get("id"))
        if full and r.get("id") in MIXED_WEAPON_PRIMARY:
            r["name"] = full["name"]
            r["nameJa"] = full["nameJa"]
    dump_json(sp, sim_rows)

    # Preserve Korean primary names across all touched data.
    protected = {}
    for filename in ["weapons.json","sim_weapons.json","decorations.json","items.json","skills.json","armors.json","sim_armors.json"]:
        p = data_dir / filename
        if p.exists():
            rows = load_json(p)
            protected[filename] = {r.get("id"): r.get("name") for r in rows if isinstance(r, dict) and r.get("id")}

    # Weapons: exact Japanese + previously verified aliases only.
    weapons = load_json(data_dir / "weapons.json")
    w_methods = Counter(); w_unresolved = []
    for w in weapons:
        row = None; method = None
        key = (norm(w.get("nameJa")), TYPE_MAP.get(w.get("weaponType")))
        hits = weapon_jp.get(key, []) if key[0] and key[1] else []
        if len(hits) == 1:
            row = hits[0]; method = "MH4U Japanese exact"
        else:
            alias = aliases.get(w.get("name"))
            if alias and alias in weapon_en:
                row = weapon_en[alias]; method = "v0.7.5 verified alias"
        if row:
            w["nameEn"] = row["name"]
            w_methods[method] += 1
        else:
            w.pop("nameEn", None)
            w_unresolved.append({"id":w.get("id"),"name":w.get("name"),"nameJa":w.get("nameJa",""),"weaponType":w.get("weaponType")})
    dump_json(data_dir / "weapons.json", weapons)

    # Compact simulator weapon rows receive nameEn too.
    sim_weapons = load_json(data_dir / "sim_weapons.json")
    by_id = {w["id"]: w for w in weapons}
    for row in sim_weapons:
        full = by_id.get(row.get("id"))
        if full and full.get("nameEn"):
            row["nameEn"] = full["nameEn"]
        else:
            row.pop("nameEn", None)
    dump_json(data_dir / "sim_weapons.json", sim_weapons)

    # Decorations: all 199 are exact Japanese matches in supplied MH4U DB.
    decorations = load_json(data_dir / "decorations.json")
    d_unresolved=[]; d_filled=0
    for d in decorations:
        hits = [r for r in item_jp.get(norm(d.get("nameJa")), []) if r.get("type") == "Decoration"]
        if len(hits)==1:
            d["nameEn"] = hits[0]["name"]; d_filled += 1
        else:
            d.pop("nameEn",None); d_unresolved.append({"id":d.get("id"),"name":d.get("name"),"nameJa":d.get("nameJa","")})
    dump_json(data_dir / "decorations.json", decorations)

    # Items: exact Japanese match only.
    items = load_json(data_dir / "items.json")
    i_unresolved=[]; i_filled=0
    for item in items:
        hits = item_jp.get(norm(item.get("nameJa")), [])
        if len(hits)==1:
            item["nameEn"] = hits[0]["name"]; i_filled += 1
        else:
            item.pop("nameEn",None); i_unresolved.append({"id":item.get("id"),"name":item.get("name"),"nameJa":item.get("nameJa","")})
    dump_json(data_dir / "items.json", items)

    # Skill trees + activation names.
    skills = load_json(data_dir / "skills.json")
    s_unresolved=[]; a_unresolved=[]; s_filled=0; a_filled=0
    for s in skills:
        tree_hits = tree_jp.get(norm(s.get("nameJa")), [])
        db_tree = tree_hits[0] if len(tree_hits)==1 else None
        if db_tree:
            s["nameEn"] = db_tree["name"]; s_filled += 1
        else:
            s.pop("nameEn",None); s_unresolved.append({"id":s.get("id"),"name":s.get("name"),"nameJa":s.get("nameJa","")})
        for a in s.get("activations", []):
            hits = skills_by_tree_points.get((int(db_tree["_id"]), int(a.get("points",0))), []) if db_tree else []
            if len(hits)==1:
                a["nameEn"] = hits[0]["name"]; a_filled += 1
            else:
                a.pop("nameEn",None); a_unresolved.append({"skill":s.get("name"),"id":a.get("id"),"name":a.get("name"),"nameJa":a.get("nameJa",""),"points":a.get("points")})
    dump_json(data_dir / "skills.json", skills)

    # Validate Korean primary names are unchanged.
    for filename, names in protected.items():
        rows = load_json(data_dir / filename)
        for r in rows:
            rid = r.get("id") if isinstance(r, dict) else None
            if rid in names and r.get("name") != names[rid]:
                raise SystemExit(f"Primary Korean name changed: {filename} / {rid}")


    # Optional Athena localization cross-check. It is not used to force conflicting English names.
    if args.athena:
        def athena_map(filename):
            with zipfile.ZipFile(args.athena) as z:
                jp = z.read("Data/Languages/Japanese/" + filename).decode("utf-8-sig").splitlines()
                en = z.read("Data/Languages/English/" + filename).decode("utf-8-sig").splitlines()
            out = defaultdict(set)
            for j, e in zip(jp, en):
                if norm(j) and e.strip(): out[norm(j)].add(e.strip())
            return out
        ath_deco = athena_map("decorations.txt")
        ath_skill = athena_map("skills.txt")
        deco_agree=[]; deco_diff=[]
        for d in decorations:
            vals=ath_deco.get(norm(d.get("nameJa")),set())
            if len(vals)==1:
                ae=next(iter(vals))
                (deco_agree if ae==d.get("nameEn") else deco_diff).append({"name":d.get("name"),"nameJa":d.get("nameJa"),"athena":ae,"mh4u":d.get("nameEn","")})
        skill_agree=[]; skill_diff=[]
        for sk in skills:
            vals=ath_skill.get(norm(sk.get("nameJa")),set())
            if len(vals)==1:
                ae=next(iter(vals))
                (skill_agree if ae==sk.get("nameEn") else skill_diff).append({"name":sk.get("name"),"nameJa":sk.get("nameJa"),"athena":ae,"mh4u":sk.get("nameEn","")})
        report["source"].append("user-supplied Athena Data.zip Japanese/English localization rows")
        report["athenaCrosscheck"]={
            "decorations":{"matched":len(deco_agree)+len(deco_diff),"englishAgreement":len(deco_agree),"englishDifferences":deco_diff},
            "skillTrees":{"matched":len(skill_agree)+len(skill_diff),"englishAgreement":len(skill_agree),"englishDifferences":skill_diff},
            "policy":"MH4U English remains canonical for this pass; Athena is used as an independent localization cross-check. Differences are recorded, not guessed away."
        }

    report["summary"] = {
        "weapons": {"total":len(weapons),"nameEnFilled":sum(bool(x.get("nameEn")) for x in weapons),"methods":dict(w_methods),"unresolved":len(w_unresolved)},
        "decorations": {"total":len(decorations),"nameEnFilled":d_filled,"unresolved":len(d_unresolved)},
        "items": {"total":len(items),"nameEnFilled":i_filled,"unresolved":len(i_unresolved)},
        "skillTrees": {"total":len(skills),"nameEnFilled":s_filled,"unresolved":len(s_unresolved)},
        "skillActivations": {"total":sum(len(s.get("activations",[])) for s in skills),"nameEnFilled":a_filled,"unresolved":len(a_unresolved)},
        "armorExisting": {"total":len(load_json(data_dir/'armors.json')),"nameEnFilled":sum(bool(x.get('nameEn')) for x in load_json(data_dir/'armors.json'))},
        "mixedPrimaryFieldsNormalized": len(MIXED_WEAPON_PRIMARY),
        "primaryKoreanWordingChanges": 0,
    }
    report["mixedWeaponPrimaryNormalization"] = normalized_mixed
    report["unresolved"] = {"weapons":w_unresolved,"decorations":d_unresolved,"items":i_unresolved,"skillTrees":s_unresolved,"skillActivations":a_unresolved}
    dump_json(root / "tools" / "core_localization_v0.7.6.json", report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
