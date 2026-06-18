import streamlit as st
import subprocess
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import date

# ── Naming banks ────────────────────────────────────────────────────────────

STRONG_SUFFIXES = [
    "hq", "hub", "group", "team", "ops", "partners", "collective", "network",
    "labs", "forge", "engine", "platform", "systems", "solutions", "direct",
    "digital", "agency", "advisors", "advisory", "consulting", "specialists",
    "experts", "pipeline", "outbound", "growth", "scale", "services", "ventures",
]
EXTENDED_SUFFIXES = [
    "app", "now", "co", "mail", "io", "works", "global", "support", "insight",
]
PREFIXES = [
    "the", "team", "with", "work", "get", "go", "try", "use", "join", "hey", "send",
]
BANNED_SUBSTR = ["-", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

RDAP = {
    "com": "https://rdap.verisign.com/com/v1/domain/",
    "net": "https://rdap.verisign.com/net/v1/domain/",
    "info": "https://rdap.identitydigital.services/rdap/domain/",
    "org": "https://rdap.publicinterestregistry.org/rdap/domain/",
}
WHOIS_SERVER = {"co": "whois.registry.co"}

# ── Core logic ──────────────────────────────────────────────────────────────

def generate(roots, words, want, pool_cap=0):
    primary = roots[0]
    secondary = roots[1:]
    out, seen = [], set()

    def add(name):
        name = name.lower()
        if name in seen:
            return
        if any(b in name for b in BANNED_SUBSTR):
            return
        seen.add(name)
        out.append(name)

    for s in STRONG_SUFFIXES:
        add(primary + s)
    for p in PREFIXES:
        add(p + primary)
    for w in words:
        add(primary + w.lower())
    for r in secondary:
        for s in STRONG_SUFFIXES:
            add(r + s)
        for p in PREFIXES:
            add(p + r)
    for s in EXTENDED_SUFFIXES:
        for r in roots:
            add(r + s)

    cap = max(pool_cap, want * 3)
    return out[:cap]


def check_rdap(fqdn, tld, tries=4):
    url = RDAP[tld] + fqdn
    for attempt in range(tries):
        try:
            r = requests.get(url, timeout=12, headers={"Accept": "application/rdap+json"})
        except requests.RequestException:
            time.sleep(1.5 * (attempt + 1))
            continue
        if r.status_code == 404:
            return "AVAILABLE"
        if r.status_code == 200:
            return "TAKEN"
        if r.status_code == 429:
            time.sleep(2.0 * (attempt + 1))
            continue
        return "UNKNOWN"
    return "UNKNOWN"


def check_whois(fqdn, server, tries=3):
    for attempt in range(tries):
        try:
            out = subprocess.run(
                ["whois", "-h", server, fqdn],
                capture_output=True, text=True, timeout=20,
            ).stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            time.sleep(1.0 * (attempt + 1))
            continue
        low = out.lower()
        if "not found" in low or "no data found" in low or "no match" in low:
            return "AVAILABLE"
        if re.search(r"domain name:\s*" + re.escape(fqdn), low) or "creation date" in low:
            return "TAKEN"
        time.sleep(1.5 * (attempt + 1))
    return "UNKNOWN"


def check_dns(fqdn):
    try:
        out = subprocess.run(
            ["dig", "+short", "NS", fqdn],
            capture_output=True, text=True, timeout=12,
        ).stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "UNKNOWN"
    return "TAKEN" if out else "AVAILABLE"


def get_checker(tld):
    if tld in RDAP:
        return lambda fqdn: check_rdap(fqdn, tld)
    if tld in WHOIS_SERVER:
        server = WHOIS_SERVER[tld]
        return lambda fqdn: check_whois(fqdn, server)
    return check_dns


def run_check(candidates, tld, progress_cb):
    check = get_checker(tld)
    workers = 6 if tld in RDAP else 2
    available, taken, unknown = [], [], []

    def do(name):
        fqdn = f"{name}.{tld}"
        status = check(fqdn)
        return fqdn, status

    total = len(candidates)
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for fqdn, status in ex.map(do, candidates):
            done += 1
            progress_cb(done / total, fqdn, status)
            if status == "AVAILABLE":
                available.append(fqdn)
            elif status == "TAKEN":
                taken.append(fqdn)
            else:
                unknown.append(fqdn)

    order = {f"{n}.{tld}": i for i, n in enumerate(candidates)}
    available.sort(key=lambda d: order.get(d, 9999))
    return available, taken, unknown


# ── UI ───────────────────────────────────────────────────────────────────────

st.title("Domain Sourcing")
st.caption("Generate and check cold-email sending domains for a client")

with st.form("domain_form"):
    col1, col2 = st.columns(2)

    with col1:
        primary_root = st.text_input(
            "Client brand root *",
            placeholder="e.g. truce",
            help="The main brand name, no spaces or hyphens"
        )
        secondary_root = st.text_input(
            "Secondary root (optional)",
            placeholder="e.g. trucesoftware",
            help="A longer variant to expand the pool"
        )

    with col2:
        tld = st.selectbox(
            "TLD",
            options=["co", "com", "net", "info", "org"],
            index=0,
            help=".co is the default — cheapest and clean-looking"
        )
        count = st.number_input(
            "How many domains to find",
            min_value=5,
            max_value=100,
            value=35,
            step=5
        )

    extra_words = st.text_input(
        "Brand/product words (optional, comma-separated)",
        placeholder="e.g. fleet, safety",
        help="Adds domain-relevant suffixes like trucesafety.co"
    )

    submitted = st.form_submit_button("Find Available Domains", type="primary", use_container_width=True)

if submitted:
    if not primary_root:
        st.error("Enter a brand root to continue.")
        st.stop()

    primary_root = primary_root.strip().lower()
    roots = [primary_root]
    if secondary_root.strip():
        roots.append(secondary_root.strip().lower())

    words = [w.strip().lower() for w in extra_words.split(",") if w.strip()] if extra_words else []

    candidates = generate(roots, words, count)

    st.divider()
    st.subheader(f"Checking {len(candidates)} candidates for .{tld}...")

    progress_bar = st.progress(0)
    status_text = st.empty()
    log_container = st.empty()
    log_lines = []

    def update_progress(pct, fqdn, status):
        progress_bar.progress(pct)
        emoji = "✅" if status == "AVAILABLE" else ("❌" if status == "TAKEN" else "⚠️")
        log_lines.append(f"{emoji} `{fqdn}` — {status}")
        status_text.markdown(f"**Checking:** `{fqdn}`")
        log_container.markdown("\n".join(log_lines[-12:]))

    available, taken, unknown = run_check(candidates, tld, update_progress)

    progress_bar.progress(1.0)
    status_text.empty()
    log_container.empty()

    buy = available[:count]
    reserves = available[count:]

    st.divider()

    col1, col2, col3 = st.columns(3)
    col1.metric("Available", len(available))
    col2.metric("Taken", len(taken))
    col3.metric("Unknown", len(unknown))

    if len(buy) < count:
        st.warning(f"Only {len(buy)} available domains found (wanted {count}). Try adding brand words or a secondary root.")

    st.subheader(f"✅ Buy These ({len(buy)})")
    st.caption("Paste this block straight into your registrar's bulk search")
    buy_text = "\n".join(buy)
    st.code(buy_text, language=None)
    st.download_button(
        "Download BUY THESE list",
        data=buy_text,
        file_name=f"{primary_root}_{tld}_{date.today().isoformat()}_buy.txt",
        mime="text/plain",
        use_container_width=True
    )

    if reserves:
        with st.expander(f"Reserves ({len(reserves)}) — use if any above are rejected at checkout"):
            st.code("\n".join(reserves), language=None)

    report_lines = [
        f"# {primary_root} — .{tld} sending domains ({date.today().isoformat()})",
        "",
        f"Roots: {', '.join(roots)}  |  wanted {count}  |  available {len(available)}",
        "",
        f"## BUY THESE ({len(buy)})",
        *buy,
        "",
        f"## Reserves ({len(reserves)})",
        *(reserves if reserves else ["(none)"]),
        "",
        f"## TAKEN ({len(taken)})",
        *(taken if taken else ["(none)"]),
    ]
    if unknown:
        report_lines += ["", f"## UNKNOWN ({len(unknown)}) — check manually", *unknown]

    st.download_button(
        "Download full report (.md)",
        data="\n".join(report_lines),
        file_name=f"{primary_root}_{tld}_{date.today().isoformat()}.md",
        mime="text/markdown",
        use_container_width=True
    )

    st.divider()
    st.caption("⚠️ Always confirm availability in the registrar cart before paying — WHOIS/RDAP can't see premium pricing or registry holds.")
