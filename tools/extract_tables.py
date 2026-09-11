#!/usr/bin/env python3
from __future__ import annotations
import json, re
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'raw_html'
MANIFEST = ROOT / 'crawl_manifest.json'
OUT = ROOT / 'raw_tables.json'


def clean(s: str) -> str:
    return re.sub(r'\s+', ' ', s.replace('\xa0', ' ')).strip()


def expand_table(table):
    """rowspan/colspan을 실제 2차원 셀로 펼친다."""
    grid = []
    spans = {}  # col -> (remaining_rows, text)
    trs = table.find_all('tr')
    for tr in trs:
        row = []
        col = 0
        cells = tr.find_all(['th', 'td'], recursive=False)
        if not cells:
            cells = tr.find_all(['th', 'td'])
        ci = 0
        while ci < len(cells) or spans:
            while col in spans:
                remain, text = spans[col]
                row.append(text)
                if remain <= 1:
                    del spans[col]
                else:
                    spans[col] = (remain - 1, text)
                col += 1
            if ci >= len(cells):
                break
            cell = cells[ci]; ci += 1
            text = clean(cell.get_text(' ', strip=True))
            rs = max(1, int(cell.get('rowspan') or 1))
            cs = max(1, int(cell.get('colspan') or 1))
            for j in range(cs):
                row.append(text)
                if rs > 1:
                    spans[col] = (rs - 1, text)
                col += 1
        if any(x for x in row):
            grid.append(row)
    width = max((len(r) for r in grid), default=0)
    return [r + [''] * (width - len(r)) for r in grid]


def nearest_title(table):
    prev = table.find_previous(['h1','h2','h3','h4','caption','strong','b','font'])
    if prev:
        t = clean(prev.get_text(' ', strip=True))
        if t:
            return t[:180]
    return ''


def manifest_lookup():
    if not MANIFEST.exists():
        return {}
    items = json.loads(MANIFEST.read_text(encoding='utf-8'))
    return {x.get('file'): x for x in items if x.get('file')}


def main():
    if not RAW.exists():
        raise SystemExit('tools/raw_html 이 없습니다. 먼저 crawl_source.py를 실행하세요.')
    meta = manifest_lookup()
    pages = []
    for f in sorted(RAW.rglob('*')):
        if not f.is_file() or f.suffix.lower() not in ('.htm','.html'):
            continue
        rel = str(f.relative_to(ROOT))
        html = f.read_text(encoding='utf-8', errors='replace')
        soup = BeautifulSoup(html, 'html.parser')
        tables = []
        for i, table in enumerate(soup.find_all('table')):
            rows = expand_table(table)
            if len(rows) < 2:
                continue
            tables.append({
                'index': i,
                'title': nearest_title(table),
                'rows': rows,
            })
        if tables:
            pages.append({
                'file': rel,
                'url': meta.get(rel, {}).get('url'),
                'page_title': meta.get(rel, {}).get('title'),
                'tables': tables,
            })
    OUT.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'페이지 {len(pages)}개 표 추출 -> {OUT}')


if __name__ == '__main__':
    main()
