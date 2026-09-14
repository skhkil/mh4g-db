#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
WEAPONS = PROJECT / "data" / "weapons.json"
OUT = ROOT / "sharpness_audit.json"
MELEE_TYPES = ["대검","태도","한손검","쌍검","해머","수렵피리","랜스","건랜스","슬래시액스","차지액스","조충곤"]
VALID_COLORS = ["red","orange","yellow","green","blue","white","purple","gray"]


def bar_ok(bar):
    if not isinstance(bar, dict) or not isinstance(bar.get("segments"), list) or not bar["segments"]:
        return False
    total = 0
    last = -1
    for seg in bar["segments"]:
        if not isinstance(seg, dict):
            return False
        color, length = seg.get("color"), seg.get("length")
        if color not in VALID_COLORS or not isinstance(length, int) or length <= 0:
            return False
        idx = VALID_COLORS.index(color)
        if idx < last:
            return False
        last = idx
        total += length
    return bar.get("total") == total


def main():
    weapons = json.loads(WEAPONS.read_text(encoding="utf-8"))
    by_type = {}
    missing_weapons = []
    partial_weapons = []
    invalid_weapons = []
    confidence = Counter()

    for wt in MELEE_TYPES:
        rows = [w for w in weapons if w.get("weaponType") == wt]
        present = complete = partial = invalid = 0
        for w in rows:
            sh = w.get("sharpness")
            if not sh:
                missing_weapons.append({k: w.get(k) for k in ("id","weaponType","name","nameJa")})
                continue
            present += 1
            confidence[sh.get("confidence", "unknown")] += 1
            normal_ok = bar_ok(sh.get("normal"))
            plus_ok = bar_ok(sh.get("plus"))
            if normal_ok and plus_ok:
                complete += 1
            else:
                partial += 1
                partial_weapons.append({
                    "id": w.get("id"), "weaponType": wt, "name": w.get("name"), "nameJa": w.get("nameJa", ""),
                    "normalValid": normal_ok, "plusValid": plus_ok, "confidence": sh.get("confidence", "unknown"),
                })
            # An existing bar with segments but inconsistent structure is an actual schema error.
            for side in ("normal", "plus"):
                bar = sh.get(side)
                if isinstance(bar, dict) and bar.get("segments") and not bar_ok(bar):
                    invalid += 1
                    invalid_weapons.append({"id": w.get("id"), "weaponType": wt, "name": w.get("name"), "side": side})
        by_type[wt] = {
            "total": len(rows), "present": present, "complete": complete, "partial": partial,
            "missing": len(rows) - present, "invalidBars": invalid,
        }

    melee_total = sum(x["total"] for x in by_type.values())
    present = sum(x["present"] for x in by_type.values())
    complete = sum(x["complete"] for x in by_type.values())
    partial = sum(x["partial"] for x in by_type.values())
    missing = sum(x["missing"] for x in by_type.values())
    ranged_with_sharpness = [
        {k:w.get(k) for k in ("id","weaponType","name","nameJa")}
        for w in weapons if w.get("weaponType") not in MELEE_TYPES and w.get("sharpness")
    ]

    report = {
        "version": "0.7.4",
        "sourceFile": "data/weapons.json",
        "rawTablesAvailable": (ROOT / "raw_tables.json").exists(),
        "policy": "원본 게이지가 없는 항목은 추측/보간하지 않음",
        "weaponTotal": len(weapons),
        "meleeTotal": melee_total,
        "sharpnessPresent": present,
        "sharpnessComplete": complete,
        "sharpnessPartial": partial,
        "sharpnessMissing": missing,
        "confidence": dict(confidence),
        "byType": by_type,
        "rangedWithSharpness": ranged_with_sharpness,
        "invalidBars": invalid_weapons,
        "missingWeapons": missing_weapons,
        "partialWeapons": partial_weapons,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "weaponTotal": report["weaponTotal"], "meleeTotal": melee_total,
        "present": present, "complete": complete, "partial": partial, "missing": missing,
        "confidence": dict(confidence), "invalidBars": len(invalid_weapons),
        "rangedWithSharpness": len(ranged_with_sharpness), "output": str(OUT),
    }, ensure_ascii=False, indent=2))
    if invalid_weapons or ranged_with_sharpness:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
