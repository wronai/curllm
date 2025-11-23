#!/usr/bin/env python3
import re
import json
from typing import Any, Dict, Optional

from .config import config

async def generic_fastpath(instruction: str, page, run_logger=None) -> Optional[Dict[str, Any]]:
    lower_instr = (instruction or "").lower()
    generic_triggers = ("extract" in lower_instr or "scrape" in lower_instr)
    specific_keywords = [
        "link","email","mail","phone","tel","telefon",
        "product","produkt","form","screenshot","captcha","bql",
    ]
    if not (generic_triggers and not any(k in lower_instr for k in specific_keywords)):
        return None
    ctx = await _page_context_min(page)
    try:
        text = await page.evaluate("() => document.body.innerText")
    except Exception:
        text = ""
    anchors = await page.evaluate(
        """
            () => Array.from(document.querySelectorAll('a')).map(a => ({
                text: (a.innerText||'').trim(),
                href: a.href
            }))
        """
    )
    emails = list(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))
    phones = list(set(re.findall(r"(?:\+\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d[\d\s-]{6,}\d", text)))
    result = {
        "title": ctx.get("title"),
        "url": ctx.get("url"),
        "links": anchors[:50],
        "emails": emails[:50],
        "phones": [p.replace(" ", "").replace("-", "") for p in phones][:50],
    }
    if run_logger:
        run_logger.log_text("Generic fast-path used (title/url/links/emails/phones)")
        run_logger.log_code("json", json.dumps(result, indent=2))
    return result

async def direct_fastpath(instruction: str, page, run_logger=None) -> Optional[Dict[str, Any]]:
    lower_instr = (instruction or "").lower()
    direct: Dict[str, Any] = {}
    if "link" in lower_instr and not (
        ("only" in lower_instr)
        and ("email" in lower_instr or "mail" in lower_instr or "phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr)
    ):
        anchors = await page.evaluate(
            """
                () => Array.from(document.querySelectorAll('a')).map(a => ({
                    text: (a.innerText||'').trim(),
                    href: a.href
                }))
            """
        )
        direct["links"] = anchors[:100]
    if "email" in lower_instr or "mail" in lower_instr:
        text = await page.evaluate("() => document.body.innerText")
        emails_text = list(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))
        emails_mailto = await page.evaluate(
            """
                () => Array.from(document.querySelectorAll('a[href^=\"mailto:\"]'))
                    .map(a => (a.getAttribute('href')||'')
                        .replace(/^mailto:/,'')
                        .split('?')[0]
                        .trim())
                    .filter(Boolean)
            """
        )
        emails = list(sorted(set(emails_text + emails_mailto)))
        direct["emails"] = emails[:100]
    if "phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr:
        text = await page.evaluate("() => document.body.innerText")
        phones_text = list(set(re.findall(r"(?:\\+\\d{1,3}[\\s-]?)?(?:\\(?\\d{2,4}\\)?[\\s-]?)?\\d[\\d\\s-]{6,}\\d", text)))
        phones_tel = await page.evaluate(
            """
                () => Array.from(document.querySelectorAll('a[href^=\"tel:\"]'))
                    .map(a => (a.getAttribute('href')||'')
                        .replace(/^tel:/,'')
                        .split('?')[0]
                        .trim())
                    .filter(Boolean)
            """
        )
        def _norm(p: str) -> str:
            return p.replace(" ", "").replace("-", "")
        phones = list(sorted(set([_norm(p) for p in (phones_text + phones_tel) if p])))
        direct["phones"] = phones[:100]
    if not direct:
        return None
    if "only" in lower_instr and (
        "email" in lower_instr or "mail" in lower_instr or "phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr
    ):
        filtered: Dict[str, Any] = {}
        if ("email" in lower_instr or "mail" in lower_instr) and "emails" in direct:
            filtered["emails"] = direct["emails"]
        if ("phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr) and "phones" in direct:
            filtered["phones"] = direct["phones"]
        direct = filtered
    if run_logger:
        run_logger.log_text("Direct extraction fast-path used:")
        run_logger.log_code("json", json.dumps(direct, indent=2))
    return direct

async def product_heuristics(instruction: str, page, run_logger=None) -> Optional[Dict[str, Any]]:
    lower_instr = (instruction or "").lower()
    if not (("product" in lower_instr or "produkt" in lower_instr) and ("under" in lower_instr or "poniżej" in lower_instr or "below" in lower_instr or re.search(r"\b(<=?|mniej niż)\b", lower_instr))):
        return None
    m = re.search(r"under\s*(\d+)|poniżej\s*(\d+)|below\s*(\d+)|mniej\s*niż\s*(\d+)", lower_instr)
    thr = None
    if m:
        for g in m.groups():
            if g:
                thr = int(g)
                break
    if thr is None:
        thr = 150
    try:
        await page.evaluate("window.scrollBy(0, window.innerHeight);")
    except Exception:
        pass
    items = await page.evaluate(
        r"""
        (thr) => {
          const asNumber = (t) => {
            const m = (t||'').replace(/\s/g,'').match(/(\d+[\.,]\d{2}|\d+)(?=\s*(?:zł|PLN|\$|€)?)/i);
            if (!m) return null;
            return parseFloat(m[1].replace(',', '.'));
          };
          const cards = Array.from(document.querySelectorAll('article, li, div'));
          const out = [];
          for (const el of cards) {
            const text = el.innerText || '';
            const price = asNumber(text);
            if (price == null || price > thr) continue;
            let a = el.querySelector('a[href]');
            const name = (a && a.innerText && a.innerText.trim()) || (text.split('\n')[0]||'').trim();
            const url = a ? a.href : null;
            if (!url || !name) continue;
            out.push({ name, price, url });
            if (out.length >= 50) break;
          }
          return out;
        }
        """,
        thr,
    )
    if isinstance(items, list) and items:
        data = {"products": items}
        if run_logger:
            run_logger.log_text("Heuristic product extraction used:")
            run_logger.log_code("json", json.dumps(data, indent=2))
        return data
    return None

async def fallback_extract(instruction: str, page, run_logger=None) -> Dict[str, Any]:
    lower_instr = (instruction or "").lower()
    fallback: Dict[str, Any] = {}
    if "link" in lower_instr:
        anchors = await page.evaluate(
            """
            () => Array.from(document.querySelectorAll('a')).map(a => ({
                text: (a.innerText||'').trim(),
                href: a.href
            }))
            """
        )
        fallback["links"] = anchors[:100]
    if "email" in lower_instr or "mail" in lower_instr:
        text = await page.evaluate("() => document.body.innerText")
        emails = list(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))
        fallback["emails"] = emails[:100]
    if "phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr:
        text = await page.evaluate("() => document.body.innerText")
        phones_text = list(set(re.findall(r"(?:\+\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d[\d\s-]{6,}\d", text)))
        phones_tel = await page.evaluate(
            """
                () => Array.from(document.querySelectorAll('a[href^=\"tel:\"]'))
                    .map(a => (a.getAttribute('href')||'')
                        .replace(/^tel:/,'')
                        .split('?')[0]
                        .trim())
                    .filter(Boolean)
            """
        )
        def _norm2(p: str) -> str:
            return p.replace(" ", "").replace("-", "")
        phones = list(sorted(set([_norm2(p) for p in (phones_text + phones_tel) if p])))
        fallback["phones"] = phones[:100]
    if not fallback:
        ctx = await _page_context_min(page)
        fallback = {"title": ctx.get("title"), "url": ctx.get("url")}
    if run_logger:
        run_logger.log_text("Fallback extraction used:")
        run_logger.log_code("json", json.dumps(fallback, indent=2))
    return fallback

async def _page_context_min(page) -> Dict[str, Any]:
    return await page.evaluate(
        """
        () => ({ title: document.title, url: window.location.href })
        """
    )


async def extract_articles_eval(page) -> Optional[list[Dict[str, Any]]]:
    """Deterministic article titles extraction using DOM evaluation.
    Returns a list of {title, url} or None if nothing meaningful was found.
    """
    items = await page.evaluate(
        r"""
        () => {
          const uniq = new Set();
          const out = [];
          const push = (title, url) => {
            title = (title||'').trim();
            if (!title) return;
            if (url) url = String(url).trim();
            const key = (url||'') + '|' + title.toLowerCase();
            if (uniq.has(key)) return; uniq.add(key);
            out.push({title, url: url||null});
          };
          const selAnchors = [
            'article h1 a','article h2 a','article h3 a',
            'main h1 a','main h2 a','main h3 a',
            'section h1 a','section h2 a','section h3 a'
          ];
          selAnchors.forEach(s => {
            document.querySelectorAll(s).forEach(a => push(a.innerText, a.href));
          });
          const selHeadings = ['article h1','article h2','article h3'];
          selHeadings.forEach(s => {
            document.querySelectorAll(s).forEach(h => {
              let url = null;
              let a = h.querySelector('a[href]');
              if (a) url = a.href; else {
                // try nearest following/preceding anchor
                let parentA = h.closest('a[href]');
                if (parentA) url = parentA.href;
              }
              push(h.innerText, url);
            });
          });
          // As a fallback, anchors in main/section that look like posts by href pattern
          const pat = /(blog|post|wpis|article|artyk|news|aktualno)/i;
          document.querySelectorAll('main a[href], section a[href]').forEach(a => {
            const t = (a.innerText||'').trim();
            if (!t) return;
            const href = a.getAttribute('href')||'';
            if (pat.test(href)) push(t, a.href);
          });
          return out.slice(0, 40);
        }
        """
    )
    if isinstance(items, list) and items:
        return items
    return None
