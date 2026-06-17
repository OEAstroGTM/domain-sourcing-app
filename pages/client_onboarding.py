import streamlit as st
import anthropic
import json
import re
from datetime import date

# ── API client ───────────────────────────────────────────────────────────────

def get_anthropic():
    key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not key:
        st.error("ANTHROPIC_API_KEY not set in Streamlit secrets.")
        st.stop()
    return anthropic.Anthropic(api_key=key)

# ── Market research ──────────────────────────────────────────────────────────

RESEARCH_SYSTEM = """You are a B2B market analyst. Research the target vertical's pain points
with depth and specificity. Use concrete numbers, workflow descriptions, tool names, and
failure modes. No generalities. No fluff. Each section should teach something actionable."""

def run_research_query(label: str, prompt: str, client: anthropic.Anthropic) -> str:
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=RESEARCH_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def build_research_queries(ctx: dict) -> list[tuple[str, str]]:
    vertical = ctx["vertical"]
    icp_role = ctx["icp_roles"]
    problem = ctx["problem_solved"]

    return [
        ("Workflow pain", (
            f"Describe the specific day-to-day workflow for {icp_role} at {vertical} companies "
            f"when they handle {problem}. What tools do they use? Where do those tools fail? "
            f"How long does each step take? Give concrete examples and data points, not generalities."
        )),
        ("Tool gaps", (
            f"How well do existing tools serve {vertical} companies trying to solve {problem}? "
            f"What do those tools miss? Why do companies in this space keep falling back on manual work? "
            f"What are the most common workarounds? Give specific numbers where possible."
        )),
        ("Scaling problems", (
            f"What happens when {vertical} companies try to scale {problem} beyond the early stage? "
            f"What breaks? What are the real failure modes? How do they work around it and at what cost?"
        )),
    ]


# ── Hypothesis generation ────────────────────────────────────────────────────

HYPOTHESIS_SYSTEM = """You are a B2B outbound strategist. Your job is to generate testable pain hypotheses
for cold email campaigns. Each hypothesis must be:
- Specific: tied to a concrete workflow step, tool failure, or scaling problem
- Quantified: includes at least one data point
- Verifiable: the recipient can confirm it from their own experience
- Connected to the product's actual value prop

Output format — always return valid JSON, no markdown fences:
{
  "hypotheses": [
    {
      "number": 1,
      "name": "Short 3-5 word label",
      "description": "2-3 sentence description — the pain, why it exists, why the product fits",
      "best_fit": "What type of company within the vertical this applies most to",
      "search_angle": "1-2 specific search queries or criteria to find companies matching this pain"
    }
  ]
}

Generate 5-7 hypotheses. No preamble. No explanation. Just the JSON."""


def generate_hypotheses(ctx: dict, research: dict, client: anthropic.Anthropic) -> list[dict]:
    research_block = "\n\n".join(
        f"### {label}\n{text}" for label, text in research.items()
    )

    prompt = f"""Client context:
- Company: {ctx['client_name']}
- Product: {ctx['product_oneliner']}
- Value prop: {ctx['value_prop']}
- ICP roles: {ctx['icp_roles']}
- ICP company size: {ctx['company_size']}
- Geography: {ctx['geography']}
- Vertical: {ctx['vertical']}
- Problem solved: {ctx['problem_solved']}
- Win cases: {ctx.get('win_cases', 'None provided')}
- Key numbers: {ctx.get('key_numbers', 'None provided')}

Market research findings:
{research_block}

Generate the hypothesis set."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=HYPOTHESIS_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    # strip markdown fences if model adds them despite instructions
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)["hypotheses"]


# ── Output formatters ─────────────────────────────────────────────────────────

def format_brief(ctx: dict) -> str:
    return f"""# Company Context

## What We Do

**Product:** {ctx['product_oneliner']}

**Value prop:** {ctx['value_prop']}

**Email-safe value prop:** {ctx.get('email_safe_vp', ctx['value_prop'])}

**Key numbers:** {ctx.get('key_numbers', '—')}

---

## Voice

**Sender:** {ctx.get('sender_name', ctx['client_name'])}

**Tone:** {ctx.get('tone', 'Professional, direct, no fluff.')}

---

## ICP

### Primary profiles

| Profile | Company size | Roles | Geographies | Why they buy |
|---------|-------------|-------|-------------|--------------|
| Primary | {ctx['company_size']} | {ctx['icp_roles']} | {ctx['geography']} | {ctx['problem_solved']} |

---

## Win Cases

{ctx.get('win_cases', 'No win cases provided yet — update after first deals close.')}

---

## Campaign History

| Campaign | Vertical | List size | Reply rate | Top hypothesis | Key learning | Date |
|----------|----------|-----------|------------|---------------|--------------|------|
| Initial | {ctx['vertical']} | — | — | — | — | {date.today().isoformat()} |

---

## Active Hypotheses

*See hypothesis_set.md*

---

## Do Not Contact

| Domain | Reason | Added |
|--------|--------|-------|
| {ctx.get('client_website', '—')} | Client own domain | {date.today().isoformat()} |
"""


def format_hypothesis_set(ctx: dict, hypotheses: list[dict]) -> str:
    lines = [f"## Hypothesis Set: {ctx['vertical']}", ""]
    for h in hypotheses:
        lines += [
            f"### #{h['number']} {h['name']}",
            h['description'],
            f"Best fit: {h['best_fit']}",
            f"Search angle: {h['search_angle']}",
            "",
        ]
    return "\n".join(lines)


def format_strategy_brief(ctx: dict, research: dict, hypotheses: list[dict]) -> str:
    research_block = "\n\n".join(
        f"### {label}\n{text}" for label, text in research.items()
    )
    hyp_block = format_hypothesis_set(ctx, hypotheses)

    return f"""# Strategy Brief — {ctx['client_name']}
Generated: {date.today().isoformat()}

---

## Client Overview

- **Product:** {ctx['product_oneliner']}
- **Value prop:** {ctx['value_prop']}
- **Target vertical:** {ctx['vertical']}
- **ICP roles:** {ctx['icp_roles']}
- **Company size:** {ctx['company_size']}
- **Geography:** {ctx['geography']}
- **Problem we solve:** {ctx['problem_solved']}

---

## Market Research

{research_block}

---

## {hyp_block}

---

## Notes for Onboarding Call

- Use the hypothesis set above to guide the strategy conversation
- Confirm which hypotheses resonate most with the client
- Ask about any verticals or company types to avoid (DNC)
- Confirm sender names and email signature format
- Confirm preferred timezone for campaign scheduling
"""


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("Client Onboarding")
st.caption("Context → Market Research → Hypotheses → Strategy Brief")

for key in ["step", "ctx", "research", "hypotheses"]:
    if key not in st.session_state:
        st.session_state[key] = 1 if key == "step" else {}

step = st.session_state.step

cols = st.columns(3)
for i, label in enumerate(["1. Client Context", "2. Market Research", "3. Hypotheses"]):
    with cols[i]:
        if i + 1 < step:
            st.success(label)
        elif i + 1 == step:
            st.info(f"**{label}**")
        else:
            st.caption(label)

st.divider()

# ── STEP 1 ───────────────────────────────────────────────────────────────────

if step == 1:
    st.subheader("Client Context")
    st.caption("Fill in what you know from the onboarding form and call. This feeds into everything.")

    with st.form("context_form"):
        client_name = st.text_input("Client / company name *", placeholder="e.g. Kindred")
        client_website = st.text_input("Website", placeholder="e.g. kindred.ai")
        product_oneliner = st.text_input("What they do (one line) *", placeholder="e.g. AI voice software with patented noise cancellation for enterprise contact centres")
        value_prop = st.text_area("Value prop *", placeholder="e.g. Reduces agent handling time by 30% by eliminating background noise on both ends of the call", height=80)
        email_safe_vp = st.text_area("Email-safe version of value prop", placeholder="Same as above but avoiding any jargon or banned words. Leave blank to use value prop.", height=80)
        key_numbers = st.text_input("Key numbers / proof points", placeholder="e.g. 30% reduction in AHT, deployed at 200+ contact centres, patented in 14 countries")

        st.divider()

        vertical = st.text_input("Target vertical *", placeholder="e.g. Enterprise contact centres, US & UK")
        icp_roles = st.text_input("ICP job titles / roles *", placeholder="e.g. VP Operations, Head of CX, Contact Centre Director")
        company_size = st.text_input("Target company size *", placeholder="e.g. 200-2,000 employees")
        geography = st.text_input("Target geography *", placeholder="e.g. United States, United Kingdom")
        problem_solved = st.text_input("Core problem we solve for them *", placeholder="e.g. Background noise degrading call quality and increasing handling time")

        st.divider()

        sender_name = st.text_input("Sender name (who emails come from)", placeholder="e.g. James Harper, Kindred")
        tone = st.text_input("Email tone", placeholder="e.g. Professional, direct. No buzzwords.", value="Professional, direct. No buzzwords or fluff.")
        win_cases = st.text_area("Win cases (optional)", placeholder="e.g. Deployed at TalkTalk — reduced AHT by 28% in first 90 days", height=80)

        submitted = st.form_submit_button("Save & Run Market Research →", type="primary", use_container_width=True)

    if submitted:
        required = {
            "client_name": client_name,
            "product_oneliner": product_oneliner,
            "value_prop": value_prop,
            "vertical": vertical,
            "icp_roles": icp_roles,
            "company_size": company_size,
            "geography": geography,
            "problem_solved": problem_solved,
        }
        missing = [k for k, v in required.items() if not v.strip()]
        if missing:
            st.error(f"Please fill in: {', '.join(missing)}")
        else:
            st.session_state.ctx = {
                "client_name": client_name.strip(),
                "client_website": client_website.strip(),
                "product_oneliner": product_oneliner.strip(),
                "value_prop": value_prop.strip(),
                "email_safe_vp": email_safe_vp.strip() or value_prop.strip(),
                "key_numbers": key_numbers.strip(),
                "vertical": vertical.strip(),
                "icp_roles": icp_roles.strip(),
                "company_size": company_size.strip(),
                "geography": geography.strip(),
                "problem_solved": problem_solved.strip(),
                "sender_name": sender_name.strip() or client_name.strip(),
                "tone": tone.strip(),
                "win_cases": win_cases.strip(),
            }
            st.session_state.step = 2
            st.rerun()

# ── STEP 2 ───────────────────────────────────────────────────────────────────

elif step == 2:
    ctx = st.session_state.ctx
    st.subheader(f"Market Research — {ctx['vertical']}")
    st.caption("Running 3 research queries via Claude to map pain points in the target vertical.")

    if not st.session_state.research:
        client = get_anthropic()
        queries = build_research_queries(ctx)
        research = {}

        for label, query in queries:
            with st.spinner(f"Researching: {label}..."):
                try:
                    result = run_research_query(label, query, client)
                    research[label] = result
                    with st.expander(f"✅ {label}", expanded=True):
                        st.markdown(result)
                except Exception as e:
                    st.warning(f"Query '{label}' failed: {e}. Continuing with partial results.")
                    research[label] = f"[Research failed: {e}]"

        st.session_state.research = research

    else:
        research = st.session_state.research
        for label, text in research.items():
            with st.expander(f"✅ {label}", expanded=False):
                st.markdown(text)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 1
            st.session_state.research = {}
            st.rerun()
    with col2:
        if st.button("Generate Hypotheses →", type="primary", use_container_width=True):
            st.session_state.step = 3
            st.rerun()

# ── STEP 3 ───────────────────────────────────────────────────────────────────

elif step == 3:
    ctx = st.session_state.ctx
    research = st.session_state.research
    st.subheader(f"Hypothesis Set — {ctx['vertical']}")
    st.caption("Campaign angles generated from client context + market research.")

    if not st.session_state.hypotheses:
        with st.spinner("Generating hypotheses with Claude..."):
            try:
                client = get_anthropic()
                hypotheses = generate_hypotheses(ctx, research, client)
                st.session_state.hypotheses = hypotheses
            except Exception as e:
                st.error(f"Hypothesis generation failed: {e}")
                st.stop()
    else:
        hypotheses = st.session_state.hypotheses

    for h in hypotheses:
        with st.expander(f"#{h['number']} — {h['name']}", expanded=True):
            st.markdown(h["description"])
            st.caption(f"**Best fit:** {h['best_fit']}")
            st.caption(f"**Search angle:** {h['search_angle']}")

    st.divider()
    st.subheader("Downloads")

    brief_md = format_brief(ctx)
    hyp_md = format_hypothesis_set(ctx, hypotheses)
    full_brief = format_strategy_brief(ctx, research, hypotheses)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "BRIEF.md",
            data=brief_md,
            file_name=f"{ctx['client_name'].lower().replace(' ', '_')}_BRIEF.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "hypothesis_set.md",
            data=hyp_md,
            file_name=f"{ctx['client_name'].lower().replace(' ', '_')}_hypotheses.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col3:
        st.download_button(
            "Full Strategy Brief",
            data=full_brief,
            file_name=f"{ctx['client_name'].lower().replace(' ', '_')}_strategy_brief.md",
            mime="text/markdown",
            use_container_width=True,
        )

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Research", use_container_width=True):
            st.session_state.step = 2
            st.session_state.hypotheses = {}
            st.rerun()
    with col2:
        if st.button("Start New Client", use_container_width=True):
            for key in ["step", "ctx", "research", "hypotheses"]:
                st.session_state[key] = 1 if key == "step" else {}
            st.rerun()
