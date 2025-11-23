#!/usr/bin/env python3
import json
from typing import Dict

async def extract_page_context(page, include_dom: bool = False, dom_max_chars: int = 20000, include_iframes: bool = True) -> Dict:
    base = await page.evaluate(
        """
        () => {
            return {
                title: document.title,
                url: window.location.href,
                text: document.body.innerText.substring(0, 5000),
                forms: Array.from(document.forms).map(f => ({
                    id: f.id,
                    action: f.action,
                    fields: Array.from(f.elements).map(e => ({
                        name: e.name,
                        type: e.type,
                        value: e.value,
                        visible: e.offsetParent !== null
                    }))
                })),
                links: Array.from(document.links).slice(0, 50).map(l => ({
                    href: l.href,
                    text: l.innerText
                })),
                buttons: Array.from(document.querySelectorAll('button')).map(b => ({
                    text: b.innerText,
                    onclick: b.onclick ? 'has handler' : null
                })),
                headings: Array.from(document.querySelectorAll('h1, h2, h3')).slice(0, 100).map(h => ({
                    tag: h.tagName.toLowerCase(),
                    text: (h.innerText||'').trim(),
                    id: h.id || undefined,
                    class: h.className || undefined
                })),
                article_candidates: (() => {
                    const anchors = Array.from(document.querySelectorAll('a[href]'));
                    const pat = /(blog|post|wpis|article|artyk|news|aktualno)/i;
                    return anchors.filter(a => {
                        const href = a.getAttribute('href') || '';
                        const t = (a.innerText||'').trim();
                        if (!t) return false;
                        return pat.test(href) || !!a.closest('article');
                    }).slice(0, 100).map(a => ({ text: (a.innerText||'').trim(), href: a.href }));
                })()
            };
        }
        """
    )
    if include_dom:
        try:
            dom_tree = await page.evaluate(
                """
                () => {
                  const SKIP = new Set(["script","style","meta","link","noscript"]);
                  function ser(n){
                    if(!n||n.nodeType!==Node.ELEMENT_NODE) return null;
                    const tag=n.tagName.toLowerCase();
                    if(SKIP.has(tag)) return null;
                    const attrs={};
                    for(const a of n.attributes){
                      if(["id","class","href","type","role","aria-label"].includes(a.name)) attrs[a.name]=a.value;
                    }
                    let text=(n.innerText||"").trim();
                    if(text && text.length>200) text=undefined;
                    const obj={tag, attrs:Object.keys(attrs).length?attrs:undefined, text:text||undefined};
                    const children=[];
                    for(const ch of n.children){ const c=ser(ch); if(c) children.push(c); }
                    if(children.length) obj.children=children;
                    return obj;
                  }
                  return ser(document.body);
                }
                """
            )
        except Exception:
            dom_tree = None
        try:
            interactive = await page.evaluate(
                """
                () => {
                  const sel = ["a[href]","button","input","textarea","select","[role=button]","[onclick]"].join(",");
                  const out=[];
                  for(const el of document.querySelectorAll(sel)){
                    out.push({
                      tag: el.tagName.toLowerCase(),
                      text: (el.innerText||"").trim()||undefined,
                      attrs: {
                        id: el.id||undefined,
                        class: el.className||undefined,
                        href: el.getAttribute("href")||undefined,
                        type: el.getAttribute("type")||undefined,
                        role: el.getAttribute("role")||undefined,
                        onclick: el.getAttribute("onclick")||undefined
                      }
                    });
                  }
                  return out;
                }
                """
            )
        except Exception:
            interactive = []
        base["interactive"] = (interactive or [])[:40]
        try:
            dom_preview = json.dumps(dom_tree)[:max(0, int(dom_max_chars))]
        except Exception:
            dom_preview = None
        if dom_preview:
            base["dom_preview"] = dom_preview
        # Optionally capture iframes (CAPTCHA, consent UIs)
        if include_iframes:
            iframes = []
            try:
                for fr in page.frames:
                    if fr == page.main_frame:
                        continue
                    try:
                        fdom = await fr.evaluate(
                            """
                            () => {
                              const SKIP = new Set(["script","style","meta","link","noscript"]);
                              function ser(n){
                                if(!n||n.nodeType!==Node.ELEMENT_NODE) return null;
                                const tag=n.tagName.toLowerCase();
                                if(SKIP.has(tag)) return null;
                                let text=(n.innerText||"").trim();
                                if(text && text.length>200) text=undefined;
                                const obj={tag, text:text||undefined};
                                const children=[];
                                for(const ch of n.children){ const c=ser(ch); if(c) children.push(c); }
                                if(children.length) obj.children=children;
                                return obj;
                              }
                              return ser(document.body);
                            }
                            """
                        )
                    except Exception:
                        fdom = None
                    try:
                        finter = await fr.evaluate(
                            """
                            () => {
                              const sel = ["a[href]","button","input","textarea","select","[role=button]","[onclick]"].join(",");
                              const out=[];
                              for(const el of document.querySelectorAll(sel)){
                                out.push({tag: el.tagName.toLowerCase(), text: (el.innerText||"").trim()||undefined});
                              }
                              return out;
                            }
                            """
                        )
                    except Exception:
                        finter = []
                    try:
                        furl = fr.url
                    except Exception:
                        furl = None
                    if fdom or finter:
                        iframes.append({"url": furl, "dom": fdom, "interactive": (finter or [])[:20]})
            except Exception:
                pass
            if iframes:
                base["iframes"] = iframes[:5]
    return base
