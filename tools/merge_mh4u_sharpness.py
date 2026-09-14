#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
WEAPONS = PROJECT / "data" / "weapons.json"
OUT = ROOT / "mh4u_sharpness_merge.json"

TYPE_MAP = {
    "대검":"Great Sword","태도":"Long Sword","한손검":"Sword and Shield","쌍검":"Dual Blades",
    "해머":"Hammer","수렵피리":"Hunting Horn","랜스":"Lance","건랜스":"Gunlance",
    "슬래시액스":"Switch Axe","차지액스":"Charge Blade","조충곤":"Insect Glaive",
}
COLORS = ["red","orange","yellow","green","blue","white","purple"]

# 기존 원본의 일본명 오타/손상 때문에 exact match가 불가능했던 26건.
# 모두 MH4U DB의 공격력/속성(또는 각성)/슬롯/회심 및 유사 일본명을 교차 확인한 명시적 매칭이다.
VERIFIED_ALIASES = {
    "클락워크":"Clockwork",
    "반역의 참인":"Seditious Edge",
    "용목의 태도【신빙】":"Dragonwood Godblade",
    "용목고태도【신참】":"Dragonwood Cutblade",
    "참로도【스사노오】":"Susano Blade",
    "밀라안세스피아":"Fatalis Ascencia",
    "파룡검【사절일문】封龍剣【邪絶一門】":"Eternal Vengeance",
    "모래 먹는 키로넥스":"Psammophages",
    "사황극 벨룸마듈라":"Amber Dalamadur",
    "봉룡검【진절일문】 封龍 剣 【 真 絶一門】":"Enduring Sacrifice",
    "봉룡검【극절일문】 封龍 剣 【極絶一門】":"Enduring Surrender",
    "에인션트블로우":"Ancient Blow",
    "블리드배싱+":"Bleeding Basher+",
    "충추【호해】+":"Tussive Gravemace+",
    "퍼퍼스매시":"Puffer Smash",
    "두추 게리오박치기":"Gypceros Ramplifi",
    "창염추 리오프로기오":"Rathalos Blueblazon",
    "젬헤드+":"Gemgalore+",
    "메테오헤드":"Meteorgalore",
    "마신추 익스팬드":"Genie's Expanse",
    "아왕�발크라노스":"Orcus Galeus",
    "화이트카타스트로프":"White Catastrophe",
    "홍창검부【광소】":"Azure Straybloom",
    "이황검부":"Futara",
    "패참부 크네무르캄":"Akantor Divider",
    "파르자다오라":"Daora's Farasa",
}

def norm_jp(text: str | None) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text or ""))

def complete(sharpness) -> bool:
    return bool(
        sharpness
        and sharpness.get("normal", {}).get("segments")
        and sharpness.get("plus", {}).get("segments")
    )

def parse_sharpness(raw: str):
    parts = (raw or "").split()
    if len(parts) != 2:
        raise ValueError(f"unexpected sharpness: {raw!r}")
    values = [[int(x) for x in part.split(".")] for part in parts]
    if any(len(v) != 7 for v in values):
        raise ValueError(f"unexpected sharpness vector: {raw!r}")
    return values

def make_bar(values, raw):
    return {
        "segments": [
            {"color": color, "length": int(value)}
            for color, value in zip(COLORS, values)
            if int(value) > 0
        ],
        "total": sum(values),
        "raw": raw,
    }

def state_counts(weapons):
    c = Counter()
    for w in weapons:
        if w.get("weaponType") not in TYPE_MAP:
            continue
        if complete(w.get("sharpness")):
            c["complete"] += 1
        elif w.get("sharpness"):
            c["partial"] += 1
        else:
            c["missing"] += 1
    return dict(c)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path, help="압축을 푼 MH4U SQLite mh4u.db 경로")
    args = parser.parse_args()

    weapons = json.loads(WEAPONS.read_text(encoding="utf-8"))
    con = sqlite3.connect(args.database)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "select w.*, i.name, i.name_jp, i.rarity from weapons w join items i on i._id=w._id"
    )]
    by_jp = {(norm_jp(r["name_jp"]), r["wtype"]): r for r in rows if r.get("name_jp")}
    by_en = {r["name"]: r for r in rows}

    before = state_counts(weapons)
    merged = []

    for w in weapons:
        if w.get("weaponType") not in TYPE_MAP or complete(w.get("sharpness")):
            continue

        row = by_jp.get((norm_jp(w.get("nameJa")), TYPE_MAP[w["weaponType"]]))
        match_method = "jp-exact"
        if row is None:
            row = by_en.get(VERIFIED_ALIASES.get(w.get("name")))
            match_method = "verified-alias"
        if row is None:
            raise SystemExit(f"unresolved weapon: {w.get('name')} / {w.get('nameJa')}")

        normal, plus = parse_sharpness(row["sharpness"])
        raw_normal, raw_plus = row["sharpness"].split()
        previous_state = "partial" if w.get("sharpness") else "missing"

        w["sharpness"] = {
            "normal": make_bar(normal, raw_normal),
            "plus": make_bar(plus, raw_plus),
            "confidence": "high",
            "method": "mh4u-db",
            "coloredDelta": sum(plus) - sum(normal),
            "source": "MonsterHunter4UDatabase/mh4u.db",
            "sourceWeaponId": row["_id"],
            "sourceName": row["name"],
            "sourceNameJa": row["name_jp"],
            "matchMethod": match_method,
        }
        merged.append({
            "id": w.get("id"),
            "weaponType": w.get("weaponType"),
            "name": w.get("name"),
            "nameJa": w.get("nameJa", ""),
            "previousState": previous_state,
            "matchMethod": match_method,
            "sourceWeaponId": row["_id"],
            "sourceName": row["name"],
            "sourceNameJa": row["name_jp"],
            "sharpness": row["sharpness"],
        })

    WEAPONS.write_text(json.dumps(weapons, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {
        "version": "0.7.5",
        "sourceDatabase": "MonsterHunter4UDatabase/app/src/main/assets/databases/mh4u.db.zip",
        "sourceRepository": "https://github.com/kamegami13/MonsterHunter4UDatabase",
        "policy": "기존 완전 예리도는 유지하고, 완전 누락/부분 누락만 외부 MH4U DB로 보강.",
        "before": before,
        "merged": len(merged),
        "matchMethods": dict(Counter(x["matchMethod"] for x in merged)),
        "previousStates": dict(Counter(x["previousState"] for x in merged)),
        "after": state_counts(weapons),
        "rows": merged,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("before","merged","matchMethods","previousStates","after")}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
