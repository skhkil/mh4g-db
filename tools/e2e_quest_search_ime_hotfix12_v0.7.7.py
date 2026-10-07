#!/usr/bin/env python3
from pathlib import Path
import json,mimetypes,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'quest_search_ime_hotfix12_e2e_v0.7.7.json'
HTML=(ROOT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="http://app.local/">',1)
def handler(route):
 u=urllib.parse.urlparse(route.request.url); rel=urllib.parse.unquote(u.path.lstrip('/')) or 'index.html'; f=(ROOT/rel).resolve()
 if not str(f).startswith(str(ROOT)) or not f.is_file(): route.fulfill(status=404,body='not found',content_type='text/plain'); return
 ct=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
 if f.suffix=='.js': ct='text/javascript'
 elif f.suffix=='.json': ct='application/json'
 route.fulfill(status=200,body=f.read_bytes(),content_type=ct)
def wait_page(pg,p): pg.wait_for_function("p=>document.querySelector('#page-'+p)?.classList.contains('active')",arg=p,timeout=30000)
errs=[]; facts=[]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 for width in (1365,390):
  pg=b.new_page(viewport={'width':width,'height':900}); pg.route('http://app.local/**',handler)
  pg.on('pageerror',lambda e,w=width:errs.append(f'{w}:pageerror:'+str(e)))
  pg.set_content(HTML,wait_until='load',timeout=60000); pg.wait_for_function("document.querySelector('#appRuntimeStatus')?.hidden===true",timeout=60000)
  pg.locator('[data-route="quest-view"][data-quest-view="key"]').evaluate('e=>e.click()'); wait_page(pg,'quest'); pg.wait_for_function("document.querySelector('#questTable tbody')",timeout=30000)
  pg.evaluate("""window.__questMut=0; window.__qobs=new MutationObserver(()=>window.__questMut++); window.__qobs.observe(document.querySelector('#questTable'),{childList:true,subtree:true});""")
  # Korean IME: composing inputs must not trigger rendering.
  pg.evaluate("""const el=document.querySelector('#questSearch');el.dispatchEvent(new CompositionEvent('compositionstart',{data:'',bubbles:true}));el.value='리';el.dispatchEvent(new InputEvent('input',{data:'리',inputType:'insertCompositionText',isComposing:true,bubbles:true}));el.value='리오';el.dispatchEvent(new InputEvent('input',{data:'오',inputType:'insertCompositionText',isComposing:true,bubbles:true}));""")
  pg.wait_for_timeout(150); during=pg.evaluate('window.__questMut')
  if during!=0: errs.append(f'{width}:render during composition={during}')
  pg.evaluate("""const el=document.querySelector('#questSearch');el.dispatchEvent(new CompositionEvent('compositionend',{data:'리오',bubbles:true}));el.dispatchEvent(new InputEvent('input',{data:'오',inputType:'insertText',bubbles:true}));""")
  pg.wait_for_timeout(50); after_end_early=pg.evaluate('window.__questMut')
  pg.wait_for_timeout(100); after=pg.evaluate('window.__questMut')
  if after_end_early!=0: errs.append(f'{width}:render too early after composition={after_end_early}')
  if after<=0: errs.append(f'{width}:no render after finalized IME input')
  # Normal rapid typing: 3 inputs should collapse into one delayed render window.
  pg.evaluate('window.__questMut=0')
  pg.evaluate("""const el=document.querySelector('#questSearch');for(const v of ['리','리오','리오레']){el.value=v;el.dispatchEvent(new InputEvent('input',{data:v.slice(-1),inputType:'insertText',bubbles:true}));}""")
  pg.wait_for_timeout(50); before_debounce=pg.evaluate('window.__questMut')
  pg.wait_for_timeout(100); after_debounce=pg.evaluate('window.__questMut')
  if before_debounce!=0: errs.append(f'{width}:render before debounce={before_debounce}')
  if after_debounce<=0: errs.append(f'{width}:no render after debounce')
  row_count=pg.locator('#questTable tbody tr').count()
  facts.append({'width':width,'duringComposition':during,'afterCompositionEnd':after,'afterCompositionEarly':after_end_early,'before90ms':before_debounce,'after90ms':after_debounce,'resultRows':row_count})
  pg.close()
 b.close()
rep={'ok':not errs,'facts':facts,'errors':errs}; OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(rep,ensure_ascii=False,indent=2));raise SystemExit(0 if rep['ok'] else 1)
