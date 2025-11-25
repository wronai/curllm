#!/usr/bin/env python3
import json
from typing import Dict, Optional

async def extract_page_context(page, include_dom: bool = False, dom_max_chars: int = 20000, include_iframes: bool = True, form_focused: bool = False) -> Dict:
    # Build JavaScript code with conditional data collection based on form_focused
    js_code = f"""
        () => {{
            const formFocused = {str(form_focused).lower()};
            const safeText = (el) => {{ try {{ return (el && el.innerText) ? String(el.innerText) : ''; }} catch(e){{ return ''; }} }};
            const safeAttr = (el, name) => {{ try {{ return (el && el.getAttribute) ? el.getAttribute(name) : null; }} catch(e){{ return null; }} }};
            const bodyText = (() => {{ try {{ return (document.body && document.body.innerText) ? document.body.innerText : ''; }} catch(e){{ return ''; }} }})();
            
            const result = {{
                title: document.title,
                url: window.location.href,
                forms: Array.from(document.forms || []).map(f => ({{
                    id: (f && f.id) || undefined,
                    action: (f && f.action) || undefined,
                    fields: Array.from((f && f.elements) || []).map(e => ({{
                        name: (e && e.name) || undefined,
                        type: (e && e.type) || undefined,
                        value: (e && e.value) || '',
                        visible: !!(e && e.offsetParent !== null),
                        required: !!(e && (e.required || e.getAttribute('aria-required') === 'true' || e.getAttribute('data-required') === 'true'))
                    }}))
                }}))
            }};
            
            // Conditional data based on form_focused
            if (formFocused) {{
                // Form-focused: minimal context
                result.text = ((bodyText||'').substring(0, 1000).trim() || undefined);
                result.links = [];  // Skip links for form tasks
                result.buttons = Array.from(document.querySelectorAll('button[type="submit"], button') || []).slice(0, 10).map(b => ({{
                    text: (safeText(b).trim() || undefined)
                }}));
                result.headings = Array.from(document.querySelectorAll('h1, h2') || [])
                    .filter(h => !!safeText(h).trim())
                    .slice(0, 5)
                    .map(h => ({{
                        tag: (h && h.tagName ? h.tagName.toLowerCase() : undefined),
                        text: safeText(h).trim()
                    }}));
            }} else {{
                // Full context for non-form tasks
                result.text = ((bodyText||'').substring(0, 5000).trim() || undefined);
                result.links = Array.from(document.links || []).slice(0, 50).map(l => ({{
                    href: (l && l.href) ? l.href : '',
                    text: (safeText(l).trim() || undefined)
                }}));
                result.buttons = Array.from(document.querySelectorAll('button') || []).map(b => ({{
                    text: (safeText(b).trim() || undefined),
                    onclick: (b && b.onclick) ? 'has handler' : undefined
                }}));
                result.headings = Array.from(document.querySelectorAll('h1, h2, h3') || [])
                    .filter(h => !!safeText(h).trim())
                    .slice(0, 100)
                    .map(h => ({{
                        tag: (h && h.tagName ? h.tagName.toLowerCase() : undefined),
                        text: safeText(h).trim(),
                        id: (h && h.id) || undefined,
                        class: (h && h.className) || undefined
                    }}));
                result.article_candidates = (() => {{
                    try {{
                        const anchors = Array.from(document.querySelectorAll('a[href]') || []);
                        const pat = /(blog|post|wpis|article|artyk|news|aktualno)/i;
                        return anchors.filter(a => {{
                            const href = safeAttr(a, 'href') || '';
                            const t = safeText(a).trim();
                            if (!t) return false;
                            try {{ return pat.test(href) || !!a.closest('article'); }} catch(e){{ return pat.test(href); }}
                        }}).slice(0, 100).map(a => ({{ text: safeText(a).trim(), href: (a && a.href) ? a.href : '' }}));
                    }} catch(e){{ return []; }}
                }})();
            }}
            
            return result;
        }}
        """
    
    base = await page.evaluate(js_code)
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
                    let text="";
                    try{ text=(n.innerText||"").trim(); }catch(e){ text=""; }
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
                      text: (()=>{ try{ return (el.innerText||"").trim()||undefined; }catch(e){ return undefined; } })(),
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
        if interactive:
            _ilist = (interactive or [])[:40]
            if _ilist:
                base["interactive"] = _ilist
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
                        entry = {"dom": fdom}
                        _fint = (finter or [])[:20]
                        if _fint:
                            entry["interactive"] = _fint
                        if furl:
                            entry["url"] = furl
                        iframes.append(entry)
            except Exception:
                pass
            if iframes:
                base["iframes"] = iframes[:5]
    return base
