#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re, time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

START = 'https://flashkiller.cafe24.com/mh4g/main.htm'
HOST = 'flashkiller.cafe24.com'
BASE_PATH = '/mh4g/'
ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'raw_html'
MANIFEST = ROOT / 'crawl_manifest.json'
MAX_PAGES = 1500
DELAY = 0.12

SKIP_EXT = re.compile(r'\.(?:jpg|jpeg|png|gif|webp|bmp|ico|css|js|zip|rar|7z|exe|mp3|wav|mp4|avi|wmv|pdf|swf)$', re.I)


def decode_html(raw: bytes, declared: str | None = None) -> str:
    # 이 사이트는 한국어 구형 HTML이므로 requests의 ISO-8859-1 기본 추정을 믿으면
    # 한글이 ÇÏÀ§ 같은 mojibake로 깨진다. META charset과 CP949/EUC-KR을 우선한다.
    head = raw[:4096].decode('ascii', errors='ignore')
    meta = re.search(r'charset\s*=\s*[\"\']?([A-Za-z0-9._-]+)', head, re.I)
    preferred = []
    if meta:
        preferred.append(meta.group(1))
    if declared and declared.lower().replace('_','-') not in {'iso-8859-1','latin-1','latin1','ascii'}:
        preferred.append(declared)
    preferred += ['cp949', 'euc-kr', 'utf-8', 'shift_jis']
    seen = set()
    for enc in preferred:
        key=(enc or '').lower().replace('_','-')
        if not key or key in seen:
            continue
        seen.add(key)
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            pass
    return raw.decode('cp949', errors='replace')


def normalize_url(url: str) -> str | None:
    url, _ = urldefrag(url)
    p = urlparse(url)
    if p.scheme not in ('http', 'https'):
        return None
    if p.netloc.lower() != HOST:
        return None
    if not p.path.startswith(BASE_PATH):
        return None
    if SKIP_EXT.search(p.path):
        return None
    # 같은 페이지의 이상한 쿼리 폭증 방지
    if len(p.query) > 250:
        return None
    return url


def local_name(url: str) -> str:
    p = urlparse(url)
    rel = p.path[len(BASE_PATH):].lstrip('/') or 'index.htm'
    if rel.endswith('/'):
        rel += 'index.htm'
    if not Path(rel).suffix:
        rel += '.htm'
    rel = re.sub(r'[^0-9A-Za-z가-힣._/-]+', '_', rel)
    if p.query:
        stem = Path(rel).stem
        suffix = Path(rel).suffix or '.htm'
        rel = str(Path(rel).with_name(f'{stem}_{hashlib.md5(p.query.encode()).hexdigest()[:8]}{suffix}'))
    return rel


def extract_links(html: str, current: str):
    soup = BeautifulSoup(html, 'html.parser')
    for tag, attr in [('a','href'),('frame','src'),('iframe','src')]:
        for node in soup.find_all(tag):
            val = node.get(attr)
            if not val:
                continue
            u = normalize_url(urljoin(current, val.strip()))
            if u:
                yield u


def page_title(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    if soup.title:
        t = soup.title.get_text(' ', strip=True)
        if t:
            return t[:160]
    return soup.get_text(' ', strip=True)[:160]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) MH4G-personal-db/0.3',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.5',
    })
    q = deque([START])
    queued = {START}
    seen = set()
    manifest = []

    while q and len(seen) < MAX_PAGES:
        url = q.popleft()
        queued.discard(url)
        if url in seen:
            continue
        seen.add(url)

        item = {'url': url, 'ok': False}
        try:
            r = session.get(url, timeout=20, allow_redirects=True)
            item['status'] = r.status_code
            r.raise_for_status()
            ctype = (r.headers.get('content-type') or '').lower()
            if 'html' not in ctype and '<html' not in r.content[:1000].lower().decode('ascii', 'ignore'):
                item['error'] = f'not html: {ctype}'
                manifest.append(item)
                continue
            html = decode_html(r.content, r.encoding)
            rel = local_name(url)
            path = RAW / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html, encoding='utf-8')
            links = list(dict.fromkeys(extract_links(html, url)))
            for u in links:
                if u not in seen and u not in queued:
                    q.append(u)
                    queued.add(u)
            item.update({
                'ok': True,
                'file': str(path.relative_to(ROOT)),
                'title': page_title(html),
                'links': links,
                'bytes': len(r.content),
            })
            print(f'[{len(seen):04d}] {r.status_code} {url}  links={len(links)}')
        except Exception as e:
            item['error'] = str(e)
            print('ERR', url, e)
        manifest.append(item)
        time.sleep(DELAY)

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    ok = sum(1 for x in manifest if x.get('ok'))
    print(f'\n완료: 성공 {ok} / 총 {len(manifest)} 페이지')
    print('manifest:', MANIFEST)


if __name__ == '__main__':
    main()
