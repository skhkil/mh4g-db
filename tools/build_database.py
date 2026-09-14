#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TABLES = ROOT / "raw_tables.json"
GEN = ROOT / "generated"
NORMALIZED = GEN / "data"
REPORT = GEN / "report.json"
PROJECT_DATA = ROOT.parent / "data"

SOURCE_ROOT = "https://flashkiller.cafe24.com/mh4g/"
APP_VERSION = "0.7.6"
PART_MAP = {"머리":"head", "몸통":"body", "팔":"arms", "허리":"waist", "다리":"legs"}

RANK_ORDER = {"low": 0, "high": 1, "g": 2}
# RARE4는 MH4G에서 하위/상위가 혼재한다. 아래 계열은 실제로 하위 단계 제작이 확인되는 예외.
RARE4_KNOWN_LOW_PREFIXES = (
    "가노스", "가디언", "헬퍼", "길드버드", "스칼러",
    "르와가", "파르메르", "킹롭스타",
)


def build_material_rank_map(items, rewards, exchanges):
    """원본 DB의 아이템/갈무리보수/용인족 교환표에서 소재의 최초 입수 등급을 만든다."""
    out = {}
    def add(name, rank):
        if not name or rank not in RANK_ORDER:
            return
        prev = out.get(name)
        if prev is None or RANK_ORDER[rank] < RANK_ORDER[prev]:
            out[name] = rank

    for x in items:
        rank = {"하위":"low", "상위":"high", "G급":"g", "G":"g"}.get(x.get("availability", ""))
        add(x.get("name"), rank)
    for x in rewards:
        add(x.get("item"), x.get("rank"))
    for x in exchanges:
        unlock = x.get("unlock", "") or ""
        rank = None
        m = re.search(r"집회소★(\d+)", unlock)
        if m:
            rank = "low" if int(m.group(1)) <= 3 else "high"
        m = re.search(r"여단★(\d+)", unlock)
        if m:
            rank = "low" if int(m.group(1)) <= 6 else "high"
        if "G★" in unlock or "G급" in unlock:
            rank = "g"
        add(x.get("result"), rank)
    return out


def infer_armor_progression_rank(rare, name, part, materials, material_rank_map=None):
    """방어구의 '최초 제작 가능 진행도' 기준 rank를 계산한다.

    원본 m1/r1은 RARE 1~4 묶음이라 RARE4의 상위 장비가 섞여 있다.
    RARE4만 이름/소재/확인된 예외를 사용해 재판정하고 나머지는 레어도 구간을 따른다.
    """
    if rare <= 3:
        return "low", "rare1-3"
    if rare >= 8:
        return "g", "rare8-10"
    if rare >= 5:
        return "high", "rare5-7"

    # RARE4 혼재 구간
    if name.startswith(RARE4_KNOWN_LOW_PREFIXES):
        return "low", "rare4-known-low"
    # 마기르는 MH4/MH4G에서 몸통/팔/허리는 하위 제작 가능, 머리/다리는 상위 소재 필요.
    if name.startswith("마기르"):
        if part in ("head", "legs"):
            return "high", "rare4-magyur-head-legs"
        return "low", "rare4-magyur-body-arms-waist"
    # S 표기는 상위 계열.
    if "S" in name:
        return "high", "rare4-S-series"

    # 원본 소재 DB에서 상위/G급에서 처음 얻는 소재가 하나라도 필요하면 상위.
    material_rank_map = material_rank_map or {}
    hits = []
    for mat_name, mat_rank in material_rank_map.items():
        if mat_rank in ("high", "g") and mat_name and mat_name in materials:
            hits.append(mat_name)
    if hits:
        return "high", "rare4-upper-material:" + ",".join(hits[:3])
    return "low", "rare4-no-upper-evidence"
WEAPON_TYPES = {
    "w1.htm":"대검", "w2.htm":"태도", "w3.htm":"한손검", "w4.htm":"쌍검",
    "w5.htm":"해머", "w6.htm":"수렵피리", "w7.htm":"랜스", "w8.htm":"건랜스",
    "w9.htm":"슬래시액스", "w10.htm":"차지액스", "w11.htm":"조충곤",
    "w12.htm":"라이트보우건", "w13.htm":"헤비보우건", "w14.htm":"활",
}
# 원본 내부의 표기 차이/명백한 오타를 원본 스킬 계통명에 맞춘다.
SKILL_ALIASES = {
    "특수회심":"특수치명타",  # 원본 스킬표: 특수치명타 / 장비표: 특수회심
    "부동":"요지부동",        # 원본 스킬표: 요지부동 / 장비표: 부동
    "발도회심":"발도치명타",  # 원본 스킬표: 발도치명타 / 일부 장비표: 발도회심
    "포슬":"포술",            # 리노프로X 일부 행 오타
    "머비":"마비",            # 람포스X 일부 행 오타
}


def repair_text(value) -> str:
    """v0.2 수집기의 ISO-8859-1 오판으로 생긴 CP949 mojibake도 복구한다."""
    s = str(value or "")
    out, buf = [], []

    def flush():
        nonlocal buf
        if not buf:
            return
        chunk = "".join(buf)
        try:
            fixed = chunk.encode("latin1").decode("cp949")
        except Exception:
            try:
                fixed = chunk.encode("latin1").decode("cp949", errors="replace")
            except Exception:
                fixed = chunk
        out.append(fixed)
        buf = []

    for ch in s:
        if ord(ch) <= 255:
            buf.append(ch)
        else:
            flush()
            out.append(ch)
    flush()
    s = "".join(out).replace("¡¡", "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def stable_id(prefix: str, *parts) -> str:
    key = "|".join(map(str, parts))
    return f"{prefix}_{hashlib.sha1(key.encode('utf-8')).hexdigest()[:12]}"


def compact_skill_name(value) -> str:
    s = repair_text(value)
    s = re.sub(r"※\s*\d+", "", s)
    s = re.sub(r"\s+", "", s)
    return s


def canonical_skill_name(value) -> str:
    name = compact_skill_name(value)
    return SKILL_ALIASES.get(name, name)


def parse_effect(value):
    s = repair_text(value)
    if not s:
        return None
    n = compact_skill_name(s)
    if n in {"몸통배가", "동계통배가"}:
        return ("__torso_up__", 1)
    # 원본 1건의 오타: 회피거리_2 -> 회피거리+2 (외부 MH4G DB로 교차 검증)
    m = re.match(r"^(.*?)_(\d+)$", s)
    if m:
        return canonical_skill_name(m.group(1)), int(m.group(2))
    m = re.match(r"^(.*?)([+-])\s*(\d+)\s*$", s)
    if not m:
        return None
    name = canonical_skill_name(m.group(1))
    points = int(m.group(3)) * (1 if m.group(2) == "+" else -1)
    return name, points


def int_loose(value, default=0):
    s = repair_text(value).replace(",", "")
    m = re.search(r"-?\d+", s)
    return int(m.group()) if m else default


def int_compact(value):
    s = repair_text(value).replace(",", "").replace(" ", "")
    return int(s) if re.fullmatch(r"\d+", s) else None


def percent(value):
    s = repair_text(value).replace(" ", "")
    m = re.fullmatch(r"([+-]?\d+)%", s)
    return int(m.group(1)) if m else 0


def slots_num(value):
    s = repair_text(value).upper().replace("○", "O").replace("●", "O")
    return min(3, s.count("O"))


def rank_from_rare(rare: int) -> str:
    # 원본 메뉴가 하위(1~4), 상위(5~7), G급(8~10)로 구분한다.
    if 1 <= rare <= 4:
        return "low"
    if 5 <= rare <= 7:
        return "high"
    if rare >= 8:
        return "g"
    return "all"


def rank_from_text(value: str) -> str:
    s = repair_text(value)
    if "하위" in s:
        return "low"
    if "상위" in s:
        return "high"
    if "G급" in s or s == "G":
        return "g"
    return "all"


def strip_tree(value: str) -> str:
    s = repair_text(value)
    s = re.sub(r"^[\s│├└─■┣┗┏┠┝┯┷]+", "", s)
    s = re.sub(r"[\s│├└─■┣┗┏┠┝┯┷]+$", "", s)
    return s.strip()


def split_weapon_name(value: str):
    s = strip_tree(value)
    if not s or s == "(일판 전용)":
        return "", ""
    m = re.match(r"^(.*?)\s*[\(（](.+)[\)）]\s*$", s)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return s, ""


def repair_text_preserve_space(value) -> str:
    """repair_text와 같은 CP949 복구를 하되 무기 파생선의 전각 공백을 보존한다."""
    s = str(value or "")
    out, buf = [], []

    def flush():
        nonlocal buf
        if not buf:
            return
        chunk = "".join(buf)
        try:
            fixed = chunk.encode("latin1").decode("cp949")
        except Exception:
            try:
                fixed = chunk.encode("latin1").decode("cp949", errors="replace")
            except Exception:
                fixed = chunk
        out.append(fixed)
        buf = []

    for ch in s:
        if ord(ch) <= 255:
            buf.append(ch)
        else:
            flush()
            out.append(ch)
    flush()
    return "".join(out).replace("\xa0", " ")


def weapon_tree_prefix(value: str) -> str:
    """원본 무기명 앞의 │├└ 및 전각 공백을 UI 표시용으로 보존한다."""
    s = repair_text_preserve_space(value)
    m = re.match(r"^([\\s\u3000│├└─┣┗┏┠┝┯┷■]+)", s)
    prefix = m.group(1) if m else ""
    return prefix.replace("■", "").rstrip()


def sharpness_run_lengths(value: str):
    """원본 예리도 셀의 색상별 l-run 길이를 복구한다."""
    s = repair_text(value)
    return [len(x) for x in re.findall(r"l+", s, flags=re.I)]


def infer_sharpness(normal_raw: str, plus_raw: str):
    """
    v0.2 raw_tables는 글자색 정보를 버렸지만 색 구간 사이의 공백은 남아 있다.
    Handicraft(+1)가 보통 5단위 만큼 색 구간을 늘리는 성질을 이용해 마지막 회색
    여백 구간인지 여부를 선택한다. 정확한 HTML 색상 메타가 있으면 향후 그 값을 우선한다.
    """
    ng, pg = sharpness_run_lengths(normal_raw), sharpness_run_lengths(plus_raw)
    if not ng and not pg:
        return None

    def candidates(groups):
        out = []
        if len(groups) <= 7:
            out.append((False, groups[:], 0))
        if groups and len(groups) - 1 <= 7:
            out.append((True, groups[:-1], groups[-1]))
        return out

    best = None
    for n_has_gray, n_colors, n_gray in candidates(ng):
        for p_has_gray, p_colors, p_gray in candidates(pg):
            if len(ng) > 7 and not n_has_gray:
                continue
            if len(pg) > 7 and not p_has_gray:
                continue
            na = n_colors + [0] * (7 - len(n_colors))
            pa = p_colors + [0] * (7 - len(p_colors))
            delta = sum(p_colors) - sum(n_colors)
            # +5가 일반적. 일부 무기는 최대 예리도 때문에 +0일 수 있다.
            delta_penalty = min(abs(delta - 5), abs(delta) + 2) * 8
            decrease_penalty = sum(max(0, na[i] - pa[i]) for i in range(7)) * 7
            last_normal = max([i for i, v in enumerate(na) if v > 0], default=-1)
            early_change = sum(abs(na[i] - pa[i]) for i in range(max(0, last_normal - 1))) * 2
            gray_penalty = 0
            if n_has_gray and p_has_gray and p_gray > n_gray:
                gray_penalty += (p_gray - n_gray) * 5
            if n_has_gray != p_has_gray:
                gray_penalty += 2
            score = delta_penalty + decrease_penalty + early_change + gray_penalty
            cand = (score, n_colors, n_gray, p_colors, p_gray, delta)
            if best is None or cand[0] < best[0]:
                best = cand

    if best is None:
        return None
    score, n_colors, n_gray, p_colors, p_gray, delta = best
    colors = ["red", "orange", "yellow", "green", "blue", "white", "purple"]

    def make_bar(vals, gray, raw):
        segs = [{"color": colors[i], "length": v} for i, v in enumerate(vals) if v > 0]
        if gray > 0:
            segs.append({"color": "gray", "length": gray})
        return {"segments": segs, "total": sum(vals) + gray, "raw": repair_text(raw)}

    return {
        "normal": make_bar(n_colors, n_gray, normal_raw),
        "plus": make_bar(p_colors, p_gray, plus_raw),
        "confidence": "high" if score <= 18 else "medium" if score <= 45 else "low",
        "method": "run-inference",
        "coloredDelta": delta,
    }


def parse_skills(pages):
    page = next((p for p in pages if (p.get("url") or "").endswith("/skill/skill.htm")), None)
    if not page:
        return []
    defs = {}
    for row in page["tables"][0]["rows"]:
        r = [repair_text(x) for x in row]
        if len(r) < 7:
            continue
        system = canonical_skill_name(r[1])
        activation = repair_text(r[4])
        pts_text = repair_text(r[3])
        if not system or not activation or system == "계통(한)":
            continue
        if re.fullmatch(r"-?\d+", pts_text):
            pts = int(pts_text)
        elif system == "식욕" and activation == "그루메":
            # 원본 표의 수치 셀이 비어 있다. MH4G 자료에서 10P 발동을 교차 검증.
            pts = 10
        else:
            continue
        rec = defs.setdefault(system, {
            "id": stable_id("skill", system),
            "name": system,
            "nameJa": repair_text(r[2]),
            "activations": [],
            "source": SOURCE_ROOT + "skill/skill.htm",
        })
        description = repair_text(r[6])
        # MH4G 교차검증 보정: 원본의 달인 -20 설명은 -10%로 중복 표기되어 있음.
        # MH4G@wiki 기준 실제 효과는 -20=-15%, -15=-10%, -10=-5%.
        if system == "달인":
            description = {
                -20:"회심률이 15% 하락.", -15:"회심률이 10% 하락.", -10:"회심률이 5% 하락.",
                10:"회심률이 10% 증가.", 15:"회심률이 15% 증가.", 20:"회심률이 20% 증가.", 30:"회심률이 30% 증가.",
            }.get(pts, description)
        if not any(a["points"] == pts and a["name"] == activation for a in rec["activations"]):
            rec["activations"].append({
                "id": stable_id("activation", system, pts, activation),
                "points": pts,
                "name": activation,
                "nameJa": repair_text(r[5]),
                "description": description,
            })
    for rec in defs.values():
        rec["activations"].sort(key=lambda a: a["points"])
    return sorted(defs.values(), key=lambda x: x["name"])


def parse_armors(pages, material_rank_map=None):
    out, unresolved = [], []
    for page in pages:
        url = page.get("url") or ""
        if "/armor/" not in url or not page.get("tables"):
            continue
        rows = page["tables"][0]["rows"]
        is_etc = url.endswith("/armor/etc.htm")
        m = re.search(r"/armor/(m[123]|r[123])\.htm", url)
        code = m.group(1) if m else ""
        page_hunter = "blade" if code.startswith("m") else ("gunner" if code.startswith("r") else None)

        for row_i, row in enumerate(rows):
            r = [repair_text(x) for x in row]
            if len(r) < 15 or r[2] not in PART_MAP or not r[3] or r[3] == "명칭(한글)":
                continue
            rare = int_loose(r[1], 0)
            hunter = page_hunter or "both"
            if is_etc and len(r) > 12:
                if r[12] == "검사": hunter = "blade"
                elif r[12] == "거너": hunter = "gunner"
                else: hunter = "both"

            skills, torso_up = {}, False
            for cell in r[5:10]:
                if not cell:
                    continue
                effect = parse_effect(cell)
                if not effect:
                    unresolved.append({"url":url, "row":row_i, "armor":r[3], "effect":cell})
                    continue
                if effect[0] == "__torso_up__":
                    torso_up = True
                else:
                    skills[effect[0]] = skills.get(effect[0], 0) + effect[1]

            if is_etc:
                price_i, defense_i, up_start, res_start, mat_i = 13, 14, 15, 23, 28
            else:
                price_i, defense_i, up_start, res_start, mat_i = 12, 13, 14, 22, 27
            materials = r[mat_i] if mat_i < len(r) else ""
            rank, rank_basis = infer_armor_progression_rank(
                rare, r[3], PART_MAP[r[2]], materials, material_rank_map
            )
            upgrades = []
            for col in range(up_start, min(up_start + 8, len(r))):
                cell = r[col]
                if cell and re.search(r"\d", cell):
                    upgrades.append(int_loose(cell, 0))
            defense = int_loose(r[defense_i], 0) if defense_i < len(r) else 0
            out.append({
                "id": stable_id("armor", url, r[3], r[2], hunter, r[11] if len(r)>11 else ""),
                "name": r[3], "nameJa": r[4] if len(r)>4 else "",
                "part": PART_MAP[r[2]], "hunterType": hunter, "rank": rank, "rare": rare,
                "gender": r[11] if len(r)>11 else "", "price": r[price_i] if price_i < len(r) else "",
                "defense": defense, "upgradeDefense": upgrades,
                "maxDefense": max(upgrades) if upgrades else defense,
                "slots": slots_num(r[10] if len(r)>10 else ""), "torsoUp": torso_up,
                "skillsByName": skills,
                "resistances": {
                    "fire": int_loose(r[res_start], 0) if res_start < len(r) else 0,
                    "water": int_loose(r[res_start+1], 0) if res_start+1 < len(r) else 0,
                    "thunder": int_loose(r[res_start+2], 0) if res_start+2 < len(r) else 0,
                    "ice": int_loose(r[res_start+3], 0) if res_start+3 < len(r) else 0,
                    "dragon": int_loose(r[res_start+4], 0) if res_start+4 < len(r) else 0,
                },
                "materials": materials, "rankBasis": rank_basis,
                "source": url, "sourceRow": row_i,
            })
    return out, unresolved


def parse_decorations(pages):
    groups, unresolved = {}, []
    for page in pages:
        url = page.get("url") or ""
        if "/accessory/" not in url or not page.get("tables"):
            continue
        for row_i, row in enumerate(page["tables"][0]["rows"]):
            r = [repair_text(x) for x in row]
            if len(r) < 8 or not r[1] or r[1].startswith("아이템 명칭"):
                continue
            name = r[1]
            if "주" not in name and "珠" not in name:
                continue
            effect = parse_effect(r[3] if len(r)>3 else "")
            if not effect or effect[0] == "__torso_up__":
                if len(r)>3 and r[3]:
                    unresolved.append({"url":url, "row":row_i, "decoration":name, "effect":r[3]})
                continue
            slots = slots_num(r[5] if len(r)>5 else name)
            key = (name, slots)
            rec = groups.setdefault(key, {
                "id": stable_id("deco", name, slots), "name":name, "nameJa":r[2] if len(r)>2 else "",
                "slots":slots, "skillsByName":{}, "materials":r[6] if len(r)>6 else "",
                "rank":rank_from_text(r[7] if len(r)>7 else ""), "source":url,
            })
            rec["skillsByName"][effect[0]] = effect[1]
            if not rec["materials"] and len(r)>6: rec["materials"] = r[6]
    return list(groups.values()), unresolved


def parse_weapons(pages):
    out = []
    melee_bases = {"w1.htm","w2.htm","w3.htm","w4.htm","w5.htm","w6.htm","w7.htm","w8.htm","w9.htm","w10.htm","w11.htm"}

    for page in pages:
        url = page.get("url") or ""
        base = url.split("/")[-1]
        if base not in WEAPON_TYPES or not page.get("tables"):
            continue
        wt = WEAPON_TYPES[base]
        table = page["tables"][0]
        raw_rows = table["rows"]
        rows = [[repair_text(x) for x in row] for row in raw_rows]

        # 페이지마다 열 위치가 조금 다르므로 헤더에서 예리도 열을 찾는다.
        sharp_i = None
        if base in melee_bases:
            for r in rows[:12]:
                for i, cell in enumerate(r):
                    if cell == "예리도":
                        sharp_i = i
                        break
                if sharp_i is not None:
                    break

        pending_base = None
        pending_sharpness = ""
        current_tree = f"{wt} 기타"
        tree_order = -1

        for row_i, r in enumerate(rows):
            raw_row = raw_rows[row_i]
            if len(r) < 2:
                continue

            # "아이언소드 파생계" 같은 원본 섹션명을 그대로 그룹 키로 사용한다.
            section = r[1].strip() if len(r) > 1 else ""
            if section.endswith("파생계"):
                current_tree = section
                tree_order += 1
                pending_base = None
                pending_sharpness = ""
                continue

            if len(r) < 4:
                continue
            namecell = r[1] if len(r)>1 else ""
            clean_name = strip_tree(namecell)
            attack_here = int_compact(r[3] if len(r)>3 else "")

            # 근접무기 표는 첫 줄=기본 예리도, 둘째 줄=무기명+예리도+1 형식이다.
            if base in melee_bases and sharp_i is not None and attack_here is not None and not clean_name:
                pending_sharpness = r[sharp_i] if len(r) > sharp_i else ""
                continue

            # 보우건은 스탯행과 이름행이 분리되어 있다.
            if base in {"w12.htm", "w13.htm"} and attack_here is not None and not clean_name:
                pending_base = r
                continue

            name, name_ja = split_weapon_name(namecell)
            if not name or name in {"명칭", "생산", "강화", "구입", "일판 전용"}:
                continue

            stat = r
            if base in {"w12.htm", "w13.htm"}:
                if pending_base is None:
                    continue
                stat = pending_base
                attack = int_compact(stat[3])
                if attack is None:
                    continue
                affinity = percent(r[17] if len(r)>17 else stat[17])
                slots = slots_num(r[18] if len(r)>18 else stat[18])
                rank_raw = r[19] if len(r)>19 else stat[19]
                price = stat[2] if len(stat)>2 else ""
                element = ""
                extra = {
                    "reloadRecoilDrift": stat[4] if len(stat)>4 else "",
                    "specialFire": stat[5] if len(stat)>5 else "",
                }
                pending_base = None
            else:
                attack = attack_here
                if attack is None:
                    continue
                if base in {"w1.htm","w2.htm","w3.htm","w4.htm","w5.htm","w7.htm"}:
                    affinity_i, slot_i, rank_i, element = 6, 7, 8, r[4] if len(r)>4 else ""
                    extra = {}
                elif base == "w6.htm":
                    affinity_i, slot_i, rank_i, element = 7, 8, 9, r[4] if len(r)>4 else ""
                    effects = []
                    start_k = max(0, row_i - 1)
                    for k in range(start_k, min(len(rows), row_i + 8)):
                        rr = rows[k]
                        if k < row_i:
                            if not (len(rr) > 3 and int_compact(rr[3]) is not None and not strip_tree(rr[1] if len(rr)>1 else "")):
                                continue
                        if k > row_i and len(rr) > 3 and int_compact(rr[3]) is not None:
                            break
                        eff = rr[10].strip() if len(rr) > 10 else ""
                        if eff and eff not in effects:
                            effects.append(eff)
                    extra = {"notes":r[5] if len(r)>5 else "", "melody":" / ".join(effects), "melodyEffects":effects}
                elif base == "w8.htm":
                    affinity_i, slot_i, rank_i, element = 7, 8, 9, r[5] if len(r)>5 else ""
                    extra = {"shelling":r[4] if len(r)>4 else ""}
                elif base in {"w9.htm","w10.htm"}:
                    affinity_i, slot_i, rank_i, element = 7, 8, 9, r[4] if len(r)>4 else ""
                    extra = {"phial":r[5] if len(r)>5 else ""}
                elif base == "w11.htm":
                    affinity_i, slot_i, rank_i, element = 6, 7, 9, r[4] if len(r)>4 else ""
                    extra = {"kinsect":r[8] if len(r)>8 else ""}
                elif base == "w14.htm":
                    affinity_i, slot_i, rank_i, element = 5, 6, 13, r[4] if len(r)>4 else ""
                    extra = {"chargeLevels":r[7:11] if len(r)>=11 else [], "arcShot":r[11] if len(r)>11 else "", "coatings":r[12] if len(r)>12 else ""}
                else:
                    continue
                affinity = percent(r[affinity_i] if len(r)>affinity_i else "")
                slots = slots_num(r[slot_i] if len(r)>slot_i else "")
                rank_raw = r[rank_i] if len(r)>rank_i else ""
                price = r[2] if len(r)>2 else ""

            # 무기명 직후 다음 스탯행 전까지의 생산/강화 소재를 현재 무기에 연결한다.
            craft = []
            for j in range(row_i + 1, min(len(rows), row_i + 6)):
                rr = rows[j]
                if len(rr) > 3 and int_compact(rr[3]) is not None:
                    break
                if len(rr) > 1 and rr[1].strip().endswith("파생계"):
                    break
                method = rr[2].strip() if len(rr) > 2 else ""
                if method in {"생산", "강화", "구입"}:
                    materials = rr[3].strip() if len(rr) > 3 else ""
                    craft.append({"method": method, "materials": materials})

            rec = {
                "id":stable_id("weapon", base, name), "name":name, "nameJa":name_ja, "weaponType":wt,
                "attack":attack, "element":element, "affinity":affinity, "slots":slots,
                "rank":rank_from_text(rank_raw), "rankRaw":rank_raw, "price":price,
                "tree":current_tree, "treeOrder":max(tree_order, 0), "rowOrder":row_i,
                "treePrefix":weapon_tree_prefix(raw_row[1] if len(raw_row)>1 else ""),
                "isFinal":"■" in repair_text_preserve_space(raw_row[1] if len(raw_row)>1 else ""),
                "craft":craft, "source":url,
            }
            if base in melee_bases and sharp_i is not None:
                plus_raw = r[sharp_i] if len(r) > sharp_i else ""
                sharp = infer_sharpness(pending_sharpness, plus_raw)
                if sharp:
                    rec["sharpness"] = sharp
                pending_sharpness = ""
            rec.update(extra)
            out.append(rec)

    # 같은 무기가 원본 표에 중복 노출될 수 있어 ID 기준 첫 레코드만 유지한다.
    unique = {}
    for rec in out:
        unique.setdefault(rec["id"], rec)
    return list(unique.values())

def parse_items(pages):
    page = next((p for p in pages if (p.get("url") or "").endswith("/item/item.htm")), None)
    if not page:
        return []
    out = []
    for row_i, row in enumerate(page["tables"][0]["rows"][3:], 3):
        r = [repair_text(x) for x in row]
        if len(r) < 10 or not r[1] or r[1] == "아이템명칭(한글)":
            continue
        rare = int_compact(r[3])
        if rare is None:
            continue
        out.append({
            "id":stable_id("item", r[1]), "name":r[1], "nameJa":r[2], "rare":rare,
            "maxStack":int_compact(r[4]) or 0, "buyPrice":r[5], "sellPrice":r[6],
            "acquire":r[7], "availability":r[8], "note":r[9], "source":page.get("url") or "",
        })
    return out



def page_rows(pages, suffix: str):
    page = next((p for p in pages if (p.get("url") or "").endswith(suffix)), None)
    if not page or not page.get("tables"):
        return []
    return [[repair_text(x) for x in row] for row in page["tables"][0]["rows"]]


def parse_weapon_summary(pages):
    rows = page_rows(pages, "/weapon/weapon_pro.htm")
    out, weapon_type = [], None
    known = set(WEAPON_TYPES.values())
    for r in rows:
        if len(r) > 2 and r[1] in known and (r[2] == r[1] or not r[2]):
            weapon_type = r[1]
            continue
        if not weapon_type or len(r) < 4:
            continue
        attr = r[1].strip()
        if not attr or attr in {"속성", "무기종류", "명칭"}:
            continue
        normal = r[2].strip()
        awaken = r[3].strip()
        if not normal and not awaken:
            continue
        if attr.endswith("속성") or attr in {"폭파", "독", "수면", "마비", "무속성"}:
            out.append({
                "id": stable_id("weapon_summary", weapon_type, attr),
                "weaponType": weapon_type, "attribute": attr,
                "normal": normal, "awaken": awaken,
                "source": SOURCE_ROOT + "weapon/weapon_pro.htm",
            })
    return out


def parse_meals(pages):
    rows = page_rows(pages, "/skill/meal.htm")
    ingredients = {"고기", "어패", "곡물", "야채", "유제품", "술"}
    methods = ["볶기", "삶기", "찌기", "튀기기"]
    out, i = [], 0
    while i < len(rows):
        r = rows[i]
        if len(r) >= 7 and r[1] in ingredients and r[2] in ingredients:
            a, b = r[1], r[2]
            group = []
            while i < len(rows):
                rr = rows[i]
                if len(rr) < 7 or rr[1] != a or rr[2] != b:
                    break
                group.append(rr)
                i += 1
            for col, method in enumerate(methods, 3):
                effect = group[0][col] if group and col < len(group[0]) else ""
                skills = []
                for gr in group[1:]:
                    value = gr[col] if col < len(gr) else ""
                    if value and value not in {"-", "－"}:
                        skills.append(value)
                out.append({
                    "id": stable_id("meal", a, b, method),
                    "ingredient1": a, "ingredient2": b, "method": method,
                    "effect": effect, "skills": skills,
                    "source": SOURCE_ROOT + "skill/meal.htm",
                })
            continue
        i += 1
    return out


def parse_monster_summary(pages):
    rows = page_rows(pages, "/monster/meat_s.htm")
    out = []
    for r in rows[4:]:
        if len(r) < 27 or not r[1] or not r[2]:
            continue
        out.append({
            "id": stable_id("monster", r[2]), "species": r[1], "name": r[2],
            "materialName": r[3], "materialJa": r[4],
            "weakspots": {"cut": r[5], "impact": r[6], "shot": r[7]},
            "elements": {"fire": r[8], "water": r[9], "thunder": r[10], "ice": r[11], "dragon": r[12]},
            "ailments": {"poison": r[13], "sleep": r[14], "paralysis": r[15], "blast": r[16]},
            "traps": {"pitfall": r[17], "shock": r[18], "flash": r[19], "sonic": r[20], "meat": r[21]},
            "special": {"roar": r[22], "wind": r[23], "tremor": r[24], "bind": r[25]},
            "traits": r[26], "source": SOURCE_ROOT + "monster/meat_s.htm",
        })
    return out


def parse_monster_details(pages):
    rows = page_rows(pages, "/monster/meat_d.htm")
    out, cur = [], None
    meta_keys = {"기본 체력": "baseHp", "최소 금관": "minCrown", "최대 은관": "maxSilver", "최대 금관": "maxGold"}
    for r in rows:
        if len(r) >= 19 and r[1] and r[1] == r[2] and r[3] == "부위":
            cur = {"id": stable_id("monster_detail", r[1]), "name": r[1], "parts": [], "statuses": [], "meta": {}, "source": SOURCE_ROOT + "monster/meat_d.htm"}
            out.append(cur)
            continue
        if cur is None or len(r) < 19:
            continue
        if r[1] in meta_keys and r[2]:
            cur["meta"][meta_keys[r[1]]] = r[2]
        if r[3] and r[3] not in {"-", "－", "부위"}:
            vals = r[4:14]
            numeric = sum(1 for x in vals if re.fullmatch(r"-?\d+", x or ""))
            if numeric >= 5:
                cur["parts"].append({
                    "part": r[3], "cut": r[4], "impact": r[5], "shot": r[6],
                    "fire": r[7], "water": r[8], "thunder": r[9], "ice": r[10], "dragon": r[11],
                    "stun": r[12], "down": r[13],
                })
        if r[14] and r[14] not in {"-", "－", "상태"} and any(r[15:19]):
            cur["statuses"].append({
                "status": r[14], "durationDamage": r[15], "initial": r[16],
                "increase": r[17], "max": r[18],
            })
    return out


def parse_monster_rewards(pages):
    rows = page_rows(pages, "/monster/galmuri.htm")
    out, current_monster, current_method, current_count = [], "", "", ""
    rank_groups = [("low", 3), ("high", 6), ("g", 9), ("extreme", 12)]
    for r in rows[4:]:
        if len(r) < 15:
            continue
        if r[1]:
            if r[1] != current_monster:
                current_monster, current_method, current_count = r[1], "", ""
        if r[2]:
            if re.fullmatch(r"\d+\s*회", r[2]):
                current_count = r[2]
            else:
                current_method, current_count = r[2], ""
        if not current_monster:
            continue
        for rank, idx in rank_groups:
            item = r[idx] if idx < len(r) else ""
            item_ja = r[idx+1] if idx+1 < len(r) else ""
            probability = r[idx+2] if idx+2 < len(r) else ""
            if item and item not in {"-", "－"} and probability and probability not in {"-", "－"}:
                out.append({
                    "id": stable_id("reward", current_monster, current_method, current_count, rank, item, probability, len(out)),
                    "monster": current_monster, "method": current_method, "count": current_count,
                    "rank": rank, "item": item, "itemJa": item_ja, "probability": probability,
                    "source": SOURCE_ROOT + "monster/galmuri.htm",
                })
    return out


def parse_dragon_exchange(pages):
    rows = page_rows(pages, "/dragonstore/exchange.htm")
    out = []
    for r in rows[5:]:
        if len(r) < 6 or not r[1] or not r[3]:
            continue
        out.append({
            "id": stable_id("exchange", r[1], r[3], r[5]),
            "result": r[1], "resultJa": r[2], "required": r[3], "requiredJa": r[4],
            "unlock": r[5], "source": SOURCE_ROOT + "dragonstore/exchange.htm",
        })
    return out


def parse_dragon_sell(pages):
    rows = page_rows(pages, "/dragonstore/sell.htm")
    out = []
    for r in rows[5:]:
        if len(r) < 5 or not r[2]:
            continue
        out.append({
            "id": stable_id("dragon_sell", r[1], r[2]),
            "line": r[1], "name": r[2], "nameJa": r[3], "points": r[4],
            "source": SOURCE_ROOT + "dragonstore/sell.htm",
        })
    return out


def parse_dragon_increase(pages):
    rows = page_rows(pages, "/dragonstore/increase.htm")
    out = []
    for r in rows[12:]:
        if len(r) < 7 or not r[1] or not r[2]:
            continue
        rare = int_compact(r[4])
        if rare is None:
            continue
        out.append({
            "id": stable_id("increase", r[1], r[2]),
            "market": r[1], "name": r[2], "nameJa": r[3], "rare": rare,
            "successRate": r[5], "points": r[6],
            "source": SOURCE_ROOT + "dragonstore/increase.htm",
        })
    return out


def parse_compositions(pages):
    rows = page_rows(pages, "/item/compose.htm")
    out = []
    for r in rows[5:]:
        if len(r) < 10 or not re.fullmatch(r"\d+", r[1] or ""):
            continue
        out.append({
            "id": stable_id("compose", r[1], r[2]), "no": int(r[1]),
            "result": r[2], "resultJa": r[3], "materialA": r[4], "materialAJa": r[5],
            "materialB": r[6], "materialBJa": r[7], "successRate": r[8], "yield": r[9],
            "source": SOURCE_ROOT + "item/compose.htm",
        })
    return out


def parse_quests(pages):
    configs = [
        ("/quest/solo_s.htm", "village", "여단"),
        ("/quest/multi_s.htm", "hub", "집회소"),
        ("/quest/multiG_s.htm", "g", "G급"),
    ]
    out = []
    for suffix, qtype, label in configs:
        rows = page_rows(pages, suffix)
        for r in rows[3:]:
            if len(r) < 12 or not r[1].startswith("★") or not r[3]:
                continue
            out.append({
                "id": stable_id("quest", qtype, r[1], r[3]),
                "questType": qtype, "questTypeLabel": label, "level": r[1],
                "key": r[2] == "○" or "키" in r[11],
                "name": r[3], "nameJa": r[4], "objective": r[5], "location": r[6],
                "fee": r[7], "reward": r[8], "time": r[9], "conditions": r[10], "note": r[11],
                "source": SOURCE_ROOT + suffix.lstrip("/"),
            })
    return out


def parse_site_info(pages):
    out = {"main": [], "history": []}
    title_rows = page_rows(pages, "/title.htm")
    seen = set()
    for r in title_rows:
        vals = [x for x in r if x]
        if not vals:
            continue
        value = vals[0]
        if value in seen:
            continue
        seen.add(value)
        if len(value) >= 2:
            out["main"].append(value)
    history_rows = page_rows(pages, "/history.htm")
    current_version, current_date = "", ""
    for r in history_rows:
        if len(r) < 5:
            continue
        if r[1] == "버전":
            continue
        if r[1]:
            current_version = r[1]
        if r[2]:
            current_date = r[2]
        if r[3]:
            out["history"].append({
                "version": current_version, "date": current_date, "content": r[3], "category": r[4] if len(r) > 4 else "",
            })
    return out


def derive_armor_sets(armors):
    from os.path import commonprefix
    grouped = {}
    for armor in armors:
        # RARE4는 같은 세트 안에서도 부위별 최초 제작 가능 등급이 다를 수 있어 rank가 아니라 rare로 묶는다.
        grouped.setdefault((armor.get("source"), armor.get("hunterType"), armor.get("rare")), []).append(armor)
    order = ["head", "body", "arms", "waist", "legs"]
    suffixes = ["헬름","캡","헤드","페이스","마스크","메일","레지스트","베스트","슈트","암","가드","글러브","클로","코일","코트","폴드","벨트","럼버","그리브","레깅스","팬츠","부츠","각반","하의","흉갑","완갑","요갑"]
    def set_name(names):
        pref = commonprefix(names).strip(" ·-_")
        if len(pref) >= 2:
            return pref
        stripped = []
        for name in names:
            s = name
            for suffix in suffixes:
                if s.endswith(suffix):
                    s = s[:-len(suffix)]
                    break
            stripped.append(s)
        pref = commonprefix(stripped).strip(" ·-_")
        if len(set(stripped)) == 1 and stripped[0]:
            return stripped[0]
        return pref if len(pref) >= 2 else names[0]
    out = []
    for (_, hunter, _rare), rows in grouped.items():
        rows = sorted(rows, key=lambda x: x.get("sourceRow", 0))
        i = 0
        while i <= len(rows) - 5:
            chunk = rows[i:i+5]
            if [x.get("part") for x in chunk] == order and len({x.get("rare") for x in chunk}) == 1:
                torso_count = sum(1 for x in chunk if x.get("torsoUp"))
                skills = {}
                for x in chunk:
                    mult = 1 + torso_count if x.get("part") == "body" else 1
                    for sid, value in (x.get("skills") or {}).items():
                        skills[sid] = skills.get(sid, 0) + value * mult
                names = [x["name"] for x in chunk]
                rank = max((x.get("rank", "low") for x in chunk), key=lambda r: RANK_ORDER.get(r, 0))
                out.append({
                    "id": stable_id("armor_set", hunter, rank, names[0]),
                    "name": set_name(names), "hunterType": hunter, "rank": rank, "rare": chunk[0].get("rare", 0),
                    "pieces": [{"id":x["id"], "part":x["part"], "name":x["name"]} for x in chunk],
                    "defense": sum(x.get("defense", 0) for x in chunk),
                    "maxDefense": sum(x.get("maxDefense", x.get("defense", 0)) for x in chunk),
                    "slots": sum(x.get("slots", 0) for x in chunk),
                    "skills": skills,
                    "resistances": {k: sum((x.get("resistances") or {}).get(k, 0) for x in chunk) for k in ["fire","water","thunder","ice","dragon"]},
                })
                i += 5
                continue
            i += 1
    return out


def derive_melodies(weapons):
    groups = {}
    for w in weapons:
        if w.get("weaponType") != "수렵피리" or not w.get("notes"):
            continue
        key = w["notes"]
        rec = groups.setdefault(key, {"id": stable_id("melody", key), "notes": key, "effects": [], "weapons": []})
        for effect in w.get("melodyEffects") or ([w.get("melody")] if w.get("melody") else []):
            if effect and effect != "선율효과" and effect not in rec["effects"]:
                rec["effects"].append(effect)
        if w["name"] not in rec["weapons"]:
            rec["weapons"].append(w["name"])
    return list(groups.values())

SIM_ARMOR_KEYS = ["id","name","nameJa","nameEn","part","hunterType","rank","defense","slots","torsoUp","resistances","materials","skills"]
SIM_WEAPON_KEYS = ["id","name","nameJa","nameEn","weaponType","attack","element","affinity","slots","rank","tree"]
SIM_ARMOR_SET_KEYS = ["id","name","hunterType","rank","pieces","slots","skills"]

def compact_rows(rows, keys):
    return [{k: row.get(k) for k in keys} for row in rows]

def summarize_sharpness(weapons):
    melee_types = [WEAPON_TYPES[f"w{i}.htm"] for i in range(1, 12)]
    by_type = {}
    missing_names = []
    partial_names = []
    complete = partial = present = missing = 0
    for wt in melee_types:
        rows = [w for w in weapons if w.get("weaponType") == wt]
        wt_present = wt_complete = wt_partial = 0
        for w in rows:
            sh = w.get("sharpness")
            if not sh:
                missing_names.append({"id": w.get("id"), "weaponType": wt, "name": w.get("name"), "nameJa": w.get("nameJa", "")})
                continue
            wt_present += 1
            is_complete = all((sh.get(side) or {}).get("segments") for side in ("normal", "plus"))
            if is_complete:
                wt_complete += 1
            else:
                wt_partial += 1
                partial_names.append({
                    "id": w.get("id"), "weaponType": wt, "name": w.get("name"), "nameJa": w.get("nameJa", ""),
                    "normal": bool((sh.get("normal") or {}).get("segments")),
                    "plus": bool((sh.get("plus") or {}).get("segments")),
                    "confidence": sh.get("confidence", ""),
                })
        wt_missing = len(rows) - wt_present
        by_type[wt] = {"total": len(rows), "present": wt_present, "complete": wt_complete, "partial": wt_partial, "missing": wt_missing}
        present += wt_present; complete += wt_complete; partial += wt_partial; missing += wt_missing
    return {
        "meleeTotal": present + missing, "present": present, "complete": complete, "partial": partial, "missing": missing,
        "byType": by_type, "missingWeapons": missing_names, "partialWeapons": partial_names,
    }


def write_simulator_compact(target_dir, armors, weapons, armor_sets):
    compact = {
        "sim_armors.json": compact_rows(armors, SIM_ARMOR_KEYS),
        "sim_weapons.json": compact_rows(weapons, SIM_WEAPON_KEYS),
        "sim_armor_sets.json": compact_rows(armor_sets, SIM_ARMOR_SET_KEYS),
    }
    for filename, rows in compact.items():
        (target_dir / filename).write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

def attach_skill_ids(records, skill_defs):
    by_name = {s["name"]:s["id"] for s in skill_defs}
    missing = Counter()
    for rec in records:
        raw = rec.pop("skillsByName", {})
        mapped = {}
        for name, value in raw.items():
            if name not in by_name:
                missing[name] += 1
                continue
            mapped[by_name[name]] = value
        rec["skills"] = mapped
    return missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()
    if not TABLES.exists():
        raise SystemExit("raw_tables.json 없음. update_db.bat 또는 crawl_source.py -> extract_tables.py 순서로 실행하세요.")
    pages = json.loads(TABLES.read_text(encoding="utf-8"))

    skills = parse_skills(pages)
    # 방어구 RARE4의 실제 제작 가능 등급 판정을 위해 소재 입수 등급 데이터를 먼저 만든다.
    items = parse_items(pages)
    monster_rewards = parse_monster_rewards(pages)
    dragon_exchange = parse_dragon_exchange(pages)
    material_rank_map = build_material_rank_map(items, monster_rewards, dragon_exchange)
    armors, armor_unresolved = parse_armors(pages, material_rank_map)
    decorations, deco_unresolved = parse_decorations(pages)
    weapons = parse_weapons(pages)
    weapon_summary = parse_weapon_summary(pages)
    meals = parse_meals(pages)
    monster_summary = parse_monster_summary(pages)
    monster_details = parse_monster_details(pages)
    dragon_sell = parse_dragon_sell(pages)
    dragon_increase = parse_dragon_increase(pages)
    compositions = parse_compositions(pages)
    quests = parse_quests(pages)
    site_info = parse_site_info(pages)

    missing_a = attach_skill_ids(armors, skills)
    missing_d = attach_skill_ids(decorations, skills)
    armor_sets = derive_armor_sets(armors)
    melodies = derive_melodies(weapons)

    NORMALIZED.mkdir(parents=True, exist_ok=True)
    datasets = {
        "armors":armors, "armor_sets":armor_sets, "decorations":decorations, "skills":skills,
        "weapons":weapons, "weapon_summary":weapon_summary, "melodies":melodies, "items":items,
        "meals":meals, "monster_summary":monster_summary, "monster_details":monster_details,
        "monster_rewards":monster_rewards, "dragon_exchange":dragon_exchange,
        "dragon_sell":dragon_sell, "dragon_increase":dragon_increase,
        "compositions":compositions, "quests":quests,
    }
    (NORMALIZED / "site_info.json").write_text(json.dumps(site_info, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, rows in datasets.items():
        (NORMALIZED / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = {name:len(rows) for name,rows in datasets.items()}
    activation_count = sum(len(s["activations"]) for s in skills)
    weapon_tree_count = len({w.get("tree") for w in weapons if w.get("tree")})
    sharpness_count = sum(1 for w in weapons if w.get("sharpness"))
    sharpness_confidence = dict(Counter(w.get("sharpness", {}).get("confidence") for w in weapons if w.get("sharpness")))
    sharpness_audit = summarize_sharpness(weapons)
    armor_rank_counts = dict(Counter(a.get("rank") for a in armors))
    armor_rank_basis_counts = dict(Counter(a.get("rankBasis", "") for a in armors))
    report = {
        "version":APP_VERSION, "counts":counts, "activationCount":activation_count,
        "weaponTreeCount":weapon_tree_count, "sharpnessCount":sharpness_count, "sharpnessConfidence":sharpness_confidence,
        "sharpnessAudit":sharpness_audit,
        "torsoUpArmorCount":sum(1 for a in armors if a.get("torsoUp")),
        "armorRankCounts":armor_rank_counts, "armorRankBasisCounts":armor_rank_basis_counts,
        "missingArmorSkillNames":dict(missing_a), "missingDecorationSkillNames":dict(missing_d),
        "unresolvedArmorEffects":armor_unresolved, "unresolvedDecorationEffects":deco_unresolved,
        "publishReady": bool(len(armors)>=2500 and len(decorations)>=150 and len(skills)>=130 and activation_count>=250 and not missing_a and not missing_d and not armor_unresolved and not deco_unresolved),
        "notes":[
            "v0.2 수집본의 CP949 mojibake를 복원함",
            "식욕→그루메는 원본 수치 셀이 비어 있어 외부 MH4G 자료로 10P를 교차 검증함",
            "회피거리_2는 외부 MH4G 장비 자료와 교차 검증하여 회피거리+2로 정규화함",
            "원본 내부 표기차이/오타 별칭을 정규화함",
            "무기는 원본의 ~파생계 구분 및 트리 기호를 저장함",
            "근접무기 예리도는 원본 표의 게이지 문자 run을 색 순서로 복원하며 confidence를 함께 기록함",
            "식사/몬스터/용인족 도매상/조합서/퀘스트/속성별 무기요약을 원본 표에서 추가 정규화함",
            "원본 메뉴에서 링크 없는 방어구 세트/몬스터 소재요약/키퀘스트/퀘스트 상세는 기존 정규화 데이터에서 파생함",
            "방어구 rank는 최초 제작 가능 진행도 기준. RARE4 혼재 문제를 S계열/원본 소재 입수등급/확인된 하위 예외로 재판정함",
        ],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.publish:
        if not report["publishReady"]:
            raise SystemExit("검증 기준 미달: 프로젝트 data/를 덮어쓰지 않았습니다.")
        PROJECT_DATA.mkdir(parents=True, exist_ok=True)
        for name in datasets:
            shutil.copy2(NORMALIZED / f"{name}.json", PROJECT_DATA / f"{name}.json")
        shutil.copy2(NORMALIZED / "site_info.json", PROJECT_DATA / "site_info.json")
        write_simulator_compact(PROJECT_DATA, armors, weapons, armor_sets)
        meta = {
            "version":APP_VERSION, "demo":False, "source":SOURCE_ROOT + "main.htm",
            "counts":counts, "activationCount":activation_count,
            "weaponTreeCount":weapon_tree_count, "sharpnessCount":sharpness_count, "sharpnessConfidence":sharpness_confidence,
            "sharpnessAudit": {k:v for k,v in sharpness_audit.items() if k not in {"missingWeapons", "partialWeapons"}},
            "note":"사용자 수집본 raw_tables.json을 CP949 복구/정규화해 생성한 실제 MH4G 데이터. RARE4 방어구는 최초 제작 가능 진행도 기준으로 재판정함.",
        }
        (PROJECT_DATA / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print("프로젝트 data/ 반영 완료")


if __name__ == "__main__":
    main()
