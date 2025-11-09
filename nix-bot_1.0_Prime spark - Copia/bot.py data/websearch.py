# websearch.py
import re, json, html
import requests
from urllib.parse import quote_plus

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NixBot/1.0"

def _clean(text: str, maxlen: int = 220) -> str:
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    return (text[: maxlen - 1] + "…") if len(text) > maxlen else text

def _domain(url: str) -> str:
    m = re.search(r"https?://([^/]+)/?", url)
    return m.group(1) if m else ""

def web_search(query: str) -> str:
    q = query.strip()
    print(f"[websearch] query = {q!r}")

    headers = {"User-Agent": UA, "Accept": "application/json,text/html;q=0.9"}
    timeout = 8

    # 1) DuckDuckGo Instant Answer (JSON)
    try:
        url = f"https://api.duckduckgo.com/?q={quote_plus(q)}&format=json&no_html=1&no_redirect=1&skip_disambig=1"
        r = requests.get(url, headers=headers, timeout=timeout)
        print(f"[websearch] DDG IA status = {r.status_code}")
        if r.ok:
            data = r.json()
            abstract = data.get("AbstractText") or data.get("Abstract")
            if abstract:
                src = data.get("AbstractSource") or data.get("Heading") or "DuckDuckGo"
                return _clean(f"{abstract} (fonte: {src})")
            rel = data.get("RelatedTopics") or []
            for item in rel:
                txt = item.get("Text")
                f_url = item.get("FirstURL")
                if txt and f_url:
                    return _clean(f"{txt} ({_domain(f_url)})")
    except Exception as e:
        print("[websearch] DDG IA error:", e)

    # 2) Wikipedia (PT e EN)
    for lang in ("pt", "en"):
        try:
            opensearch = f"https://{lang}.wikipedia.org/w/api.php?action=opensearch&search={quote_plus(q)}&limit=1&namespace=0&format=json"
            ro = requests.get(opensearch, headers=headers, timeout=timeout)
            print(f"[websearch] wiki {lang} opensearch status = {ro.status_code}")
            if ro.ok:
                arr = ro.json()
                if len(arr) >= 4 and arr[1]:
                    title = arr[1][0]
                    sum_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote_plus(title)}"
                    rs = requests.get(sum_url, headers=headers, timeout=timeout)
                    print(f"[websearch] wiki {lang} summary status = {rs.status_code}")
                    if rs.ok:
                        jd = rs.json()
                        extract = jd.get("extract")
                        if extract:
                            return _clean(f"{extract} (wikipedia.{lang})")
        except Exception as e:
            print(f"[websearch] wiki {lang} error:", e)

    # 3) DuckDuckGo HTML (fallback)
    try:
        html_url = f"https://duckduckgo.com/html/?q={quote_plus(q)}"
        rh = requests.get(html_url, headers={"User-Agent": UA}, timeout=timeout)
        print(f"[websearch] DDG HTML status = {rh.status_code}")
        if rh.ok:
            m = re.search(
                r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
                rh.text, flags=re.S
            )
            if m:
                url = html.unescape(m.group(1))
                title = _clean(re.sub("<.*?>", "", m.group(2)))
                snippet = _clean(re.sub("<.*?>", "", m.group(3)))
                dom = _domain(url)
                return _clean(f"{title}: {snippet} ({dom})")
    except Exception as e:
        print("[websearch] DDG HTML error:", e)

    return "Não encontrei nada confiável agora."
