"""Heuristic, page-level extraction. All functions are pure (HTML in, data out)."""
from __future__ import annotations

import json
import re
from typing import Dict, List
from urllib.parse import urlparse

from bs4 import BeautifulSoup

# --------------------------------------------------------------------- regex
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![\w/])(\+?\d[\d\s().-]{7,18}\d)(?![\w/])")
FOUNDED_RE = re.compile(
    r"\b(?:founded|established|since|incorporated|started)\s*(?:in|on)?\s*"
    r"(?:[A-Z][a-z]+\.?\s+(?:\d{1,2},?\s+)?)?((?:19|20)\d{2})\b", re.I)
BAD_EMAIL_PARTS = ("example.", "sentry", "wixpress", "domain.com", "your", "email@",
                   "@2x", "u003e")
BAD_EMAIL_TLDS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js")

SOCIAL_PATTERNS = {
    "linkedin": re.compile(r"linkedin\.com/(company|school)/[\w.%-]+", re.I),
    "twitter": re.compile(r"(?:twitter|x)\.com/(?!share|intent|home)[\w]{1,30}/?$", re.I),
    "facebook": re.compile(r"facebook\.com/(?!sharer|share)[\w.-]+/?$", re.I),
    "instagram": re.compile(r"instagram\.com/[\w.]+/?$", re.I),
    "github": re.compile(r"github\.com/[\w-]+/?$", re.I),
    "youtube": re.compile(r"youtube\.com/(?:c/|channel/|user/|@)[\w-]+", re.I),
}

# Technology fingerprints searched in raw HTML (scripts, meta tags, asset URLs).
TECH_SIGNATURES = {
    "React": r"react(?:\.min)?\.js|data-reactroot|__REACT_DEVTOOLS|react-dom",
    "Next.js": r"/_next/|__NEXT_DATA__",
    "Vue.js": r"vue(?:\.min)?\.js|data-v-[0-9a-f]{6,}|__VUE__",
    "Nuxt": r"/_nuxt/|__NUXT__",
    "Angular": r"ng-version=|angular(?:\.min)?\.js",
    "Svelte": r"svelte-[a-z0-9]{5,}|/_app/immutable/",
    "jQuery": r"jquery[\w.-]*\.js",
    "Bootstrap": r"bootstrap(?:\.min)?\.(?:css|js)",
    "Tailwind CSS": r"tailwind(?:css)?[\w.-]*\.css|cdn\.tailwindcss\.com",
    "WordPress": r"wp-content|wp-includes|name=\"generator\" content=\"WordPress",
    "Shopify": r"cdn\.shopify\.com|Shopify\.theme",
    "Wix": r"wixstatic\.com|X-Wix-",
    "Squarespace": r"squarespace\.com|static1\.squarespace",
    "Webflow": r"webflow\.com|data-wf-page",
    "Drupal": r"drupal-settings-json|/sites/default/files",
    "Gatsby": r"___gatsby|gatsby-",
    "Google Analytics": r"google-analytics\.com|googletagmanager\.com/gtag|gtag\(",
    "Google Tag Manager": r"googletagmanager\.com/gtm\.js",
    "HubSpot": r"js\.hs-scripts\.com|hubspot\.com|hs-analytics",
    "Intercom": r"widget\.intercom\.io|intercomSettings",
    "Segment": r"cdn\.segment\.com|analytics\.js/v1",
    "Stripe": r"js\.stripe\.com",
    "Cloudflare": r"cdnjs\.cloudflare\.com|cloudflare|__cf_bm",
    "AWS": r"amazonaws\.com|cloudfront\.net",
    "Google Cloud": r"storage\.googleapis\.com|gstatic\.com/firebasejs",
    "Firebase": r"firebase(?:app|io)\.com|firebasejs",
    "Vercel": r"vercel\.app|_vercel",
    "Netlify": r"netlify\.app|netlify",
    "Sentry": r"sentry\.io|browser\.sentry-cdn",
    "Hotjar": r"static\.hotjar\.com",
    "Zendesk": r"zdassets\.com|zendesk\.com",
}
# Technologies often named in prose (careers pages, product copy, blog posts).
TECH_KEYWORDS = [
    "Python", "Java", "JavaScript", "TypeScript", "Rust", "Kotlin", "Scala", "Node.js",
    "Django", "Flask", "FastAPI", "Spring Boot", "Ruby on Rails", "Kubernetes", "Docker",
    "Terraform", "Ansible", "OpenStack", "AWS", "Azure", "Google Cloud", "PostgreSQL",
    "MySQL", "MongoDB", "Redis", "Elasticsearch", "Kafka", "RabbitMQ", "GraphQL",
    "TensorFlow", "PyTorch", "Spark", "Snowflake", "Prometheus", "Grafana", "Linux",
]

INDUSTRY_KEYWORDS = {
    "Cloud Computing": ["cloud", "iaas", "paas", "saas", "hosting", "kubernetes", "devops"],
    "Artificial Intelligence": ["machine learning", "artificial intelligence", "deep learning", "llm", " ai "],
    "Cybersecurity": ["cybersecurity", "security platform", "threat", "zero trust", "encryption"],
    "Fintech": ["fintech", "payments", "banking", "lending", "insurtech"],
    "E-commerce": ["e-commerce", "ecommerce", "online store", "marketplace", "retail"],
    "Healthcare": ["healthcare", "medical", "clinical", "patient", "biotech", "pharma"],
    "Data & Analytics": ["analytics", "data platform", "business intelligence", "data warehouse"],
    "Software Development": ["software development", "web development", "app development", "consulting", "agency"],
    "Telecommunications": ["telecom", "5g", "network operator", "connectivity"],
    "Education": ["edtech", "e-learning", "online courses", "students"],
    "Energy & Cleantech": ["renewable", "solar", "clean energy", "battery", "sustainab"],
    "Logistics": ["logistics", "supply chain", "freight", "shipping"],
}

COMPETITOR_RE = re.compile(
    r"(?:alternatives? to|competitors? (?:include|such as|like)|compared (?:to|with)|"
    r"\bvs\.?|versus|unlike|switch(?:ing)? from|instead of)\s+"
    r"((?:[A-Z][\w&.\-]*)(?:\s+[A-Z][\w&.\-]*){0,2})")
PROJECT_HINTS = re.compile(
    r"\b(?:currently|now|we(?:'re| are)|just|recently|actively)\s+"
    r"(?:working on|building|developing|launching|rolling out|expanding|researching|piloting|"
    r"launched|released|announced)\b[^.!?\n]{10,160}", re.I)
LEADER_RE = re.compile(r"\b(?:leading|#1|number one|largest|market leader|pioneer|"
                       r"world'?s (?:first|best|leading)|most trusted)\b", re.I)
CHALLENGER_RE = re.compile(r"\b(?:alternative to|challenger|disrupt\w*|faster than|cheaper than|"
                           r"rethink\w*|next-generation|reinvent\w*)\b", re.I)
NICHE_RE = re.compile(r"\b(?:specialis\w+|boutique|niche|focused on|dedicated to|purpose-built)\b", re.I)


# ------------------------------------------------------------------ helpers
def soup_of(html: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:  # pragma: no cover - lxml missing
        return BeautifulSoup(html, "html.parser")


def clean(text: str, limit: int = 0) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:limit].rstrip() if limit else text


def visible_text(soup: BeautifulSoup) -> str:
    s = BeautifulSoup(str(soup), "html.parser")
    for t in s(["script", "style", "noscript", "template", "svg"]):
        t.decompose()
    return clean(s.get_text(" "))


def _dedupe(items) -> List:
    seen, out = set(), []
    for i in items:
        key = i.lower() if isinstance(i, str) else i
        if i and key not in seen:
            seen.add(key)
            out.append(i)
    return out


def json_ld_objects(soup: BeautifulSoup) -> List[dict]:
    objs: List[dict] = []

    def walk(node):
        if isinstance(node, list):
            for n in node:
                walk(n)
        elif isinstance(node, dict):
            objs.append(node)
            walk(node.get("@graph", []))

    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            walk(json.loads(tag.string or tag.get_text() or ""))
        except (ValueError, TypeError):
            continue
    return objs


def _is_org(obj: dict) -> bool:
    t = obj.get("@type", "")
    t = t if isinstance(t, list) else [t]
    return any(x in ("Organization", "Corporation", "LocalBusiness", "NGO", "OnlineBusiness",
                     "ProfessionalService", "SoftwareCompany") or str(x).endswith("Business")
               for x in t)


# ---------------------------------------------------------------- extractors
def extract_name(soup: BeautifulSoup, url: str, ld: List[dict]) -> str:
    for o in ld:
        if _is_org(o) and isinstance(o.get("name"), str) and o["name"].strip():
            return clean(o["name"], 100)
    for attrs in ({"property": "og:site_name"}, {"name": "application-name"}):
        m = soup.find("meta", attrs=attrs)
        if m and m.get("content", "").strip():
            return clean(m["content"], 100)
    if soup.title and soup.title.string:
        parts = [p.strip() for p in re.split(r"\s[|\-–—:·•]\s", soup.title.string) if p.strip()]
        if parts:
            host = urlparse(url).netloc.lower().replace("www.", "").split(".")[0]
            for p in parts:  # prefer the segment resembling the domain
                if host and host in re.sub(r"[^a-z0-9]", "", p.lower()):
                    return clean(p, 100)
            return clean(min(parts, key=len) if len(parts) > 2 else parts[0], 100)
    host = urlparse(url).netloc.lower().replace("www.", "").split(".")[0]
    return host.capitalize()


def extract_emails(soup: BeautifulSoup, html: str) -> List[str]:
    found = []
    for a in soup.select('a[href^="mailto:"]'):
        found.append(a["href"][7:].split("?")[0])
    found += EMAIL_RE.findall(visible_text(soup))
    out = []
    for e in found:
        e = e.strip().strip(".,;:").lower()
        if any(b in e for b in BAD_EMAIL_PARTS) or e.endswith(BAD_EMAIL_TLDS):
            continue
        if EMAIL_RE.fullmatch(e):
            out.append(e)
    return _dedupe(out)


def extract_phones(soup: BeautifulSoup) -> List[str]:
    found = [a["href"][4:].strip() for a in soup.select('a[href^="tel:"]')]
    for m in PHONE_RE.findall(visible_text(soup)):
        digits = re.sub(r"\D", "", m)
        if not 8 <= len(digits) <= 15:
            continue
        if re.fullmatch(r"(?:19|20)\d{2}[-/. ]\d{1,2}[-/. ]\d{1,2}", m.strip()):
            continue  # a date
        if not re.search(r"[\s().+-]", m):
            continue  # bare digit run (IDs, timestamps)
        found.append(m)
    return _dedupe(clean(p) for p in found if 8 <= len(re.sub(r"\D", "", p)) <= 15)


def extract_socials(soup: BeautifulSoup) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0].split("#")[0]
        for net, pat in SOCIAL_PATTERNS.items():
            if net not in out and pat.search(href):
                out[net] = href
    return out


def extract_address(soup: BeautifulSoup, ld: List[dict]) -> str:
    for o in ld:
        addr = o.get("address")
        if isinstance(addr, dict):
            parts = [addr.get(k) for k in ("streetAddress", "addressLocality", "addressRegion",
                                            "postalCode", "addressCountry")]
            parts = [p["name"] if isinstance(p, dict) else p for p in parts]
            joined = ", ".join(str(p) for p in parts if p)
            if joined:
                return clean(joined, 250)
        elif isinstance(addr, str) and addr.strip():
            return clean(addr, 250)
    tag = soup.find("address")
    if tag:
        return clean(tag.get_text(" "), 250)
    el = soup.find(attrs={"itemprop": "address"})
    return clean(el.get_text(" "), 250) if el else ""


def extract_description(soup: BeautifulSoup, ld: List[dict]) -> str:
    for attrs in ({"name": "description"}, {"property": "og:description"}):
        m = soup.find("meta", attrs=attrs)
        if m and len(m.get("content", "").strip()) > 20:
            return clean(m["content"], 400)
    for o in ld:
        if _is_org(o) and isinstance(o.get("description"), str):
            return clean(o["description"], 400)
    p = next((p for p in soup.find_all("p") if len(p.get_text(strip=True)) > 60), None)
    return clean(p.get_text(" "), 400) if p else ""


def extract_tagline(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if h1 and 3 < len(h1.get_text(strip=True)) < 160:
        return clean(h1.get_text(" "), 160)
    m = soup.find("meta", attrs={"property": "og:title"})
    return clean(m["content"], 160) if m and m.get("content") else ""


def extract_founded(text: str, ld: List[dict]) -> str:
    for o in ld:
        fd = o.get("foundingDate")
        if isinstance(fd, (str, int)) and re.search(r"(?:19|20)\d{2}", str(fd)):
            return re.search(r"(?:19|20)\d{2}", str(fd)).group(0)
    m = FOUNDED_RE.search(text)
    return m.group(1) if m else ""


def extract_industry(text: str, ld: List[dict]) -> str:
    low = f" {text.lower()} "
    scores = {ind: sum(low.count(k) for k in kws) for ind, kws in INDUSTRY_KEYWORDS.items()}
    ind, score = max(scores.items(), key=lambda kv: kv[1])
    return ind if score >= 2 else ""


def extract_products(soup: BeautifulSoup, is_product_page: bool, ld: List[dict]) -> List[str]:
    items: List[str] = []
    for o in ld:
        t = o.get("@type")
        if t in ("Product", "Service") and isinstance(o.get("name"), str):
            items.append(clean(o["name"], 80))
    if is_product_page:
        for h in soup.find_all(["h2", "h3"]):
            t = clean(h.get_text(" "), 80)
            if 3 <= len(t) <= 80 and not re.search(r"contact|subscribe|newsletter|cookie|follow us|©", t, re.I):
                items.append(t)
    return _dedupe(items)[:12]


def extract_tech(html: str, text: str) -> List[str]:
    found = [name for name, pat in TECH_SIGNATURES.items() if re.search(pat, html, re.I)]
    for kw in TECH_KEYWORDS:
        if re.search(rf"(?<![\w.]){re.escape(kw)}(?![\w])", text):
            found.append(kw)
    return _dedupe(found)


def extract_projects(soup: BeautifulSoup, text: str, is_project_page: bool) -> List[str]:
    items = [clean(m.group(0), 200) for m in PROJECT_HINTS.finditer(text)]
    if is_project_page:
        for h in soup.find_all(["h2", "h3"]):
            t = clean(h.get_text(" "), 120)
            if 8 <= len(t) <= 120 and not re.search(r"subscribe|newsletter|cookie|related|share", t, re.I):
                items.append(t)
    return _dedupe(items)[:10]


def extract_competitors(text: str, own_name: str = "") -> List[str]:
    out = []
    for m in COMPETITOR_RE.finditer(text):
        name = m.group(1).strip(" .,-")
        name = re.sub(r"\s+(?:and|or|is|are|the|for|to)$", "", name, flags=re.I)
        if len(name) > 1 and name.lower() != own_name.lower() and name.lower() not in {"the", "our", "we"}:
            out.append(name)
    return _dedupe(out)[:10]


def extract_positioning(text: str) -> str:
    for label, rx in (("Market leader", LEADER_RE), ("Challenger", CHALLENGER_RE), ("Niche specialist", NICHE_RE)):
        m = rx.search(text)
        if m:
            s = max(0, m.start() - 70)
            snippet = clean(text[s:m.end() + 90])
            return f"{label}: \"...{snippet}...\""
    return ""


def extract_links(soup: BeautifulSoup, base_url: str) -> List[tuple]:
    from urllib.parse import urljoin
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        out.append((urljoin(base_url, href).split("#")[0], clean(a.get_text(" "), 80)))
    return out


def extract_page(html: str, url: str, page_kind: str = "home") -> dict:
    """Extract every signal from one page. ``page_kind`` is home/contact/about/products/projects/other."""
    soup = soup_of(html)
    ld = json_ld_objects(soup)
    text = visible_text(soup)
    name = extract_name(soup, url, ld)
    return {
        "name": name,
        "emails": extract_emails(soup, html),
        "phones": extract_phones(soup),
        "social_profiles": extract_socials(soup),
        "address": extract_address(soup, ld),
        "tagline": extract_tagline(soup),
        "description": extract_description(soup, ld),
        "founded": extract_founded(text, ld),
        "industry": extract_industry(text, ld),
        "products_services": extract_products(soup, page_kind == "products", ld),
        "tech_stack": extract_tech(html, text),
        "current_projects": extract_projects(soup, text, page_kind == "projects"),
        "competitors": extract_competitors(text, name),
        "market_positioning": extract_positioning(text),
        "_links": extract_links(soup, url),
        "_text": text,
    }
