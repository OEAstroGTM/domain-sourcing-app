import streamlit as st
import anthropic
import json
import re

HYPOTHESIS_SYSTEM = """You are a B2B outbound strategist. Generate testable pain hypotheses for cold email campaigns.

Each hypothesis must be:
- Specific: tied to a concrete workflow step, tool failure, or scaling problem
- Quantified: includes at least one data point
- Verifiable: the recipient can confirm it from their own experience
- Connected to the product's actual value prop

Output valid JSON only — no markdown fences, no preamble:
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

Generate 5-7 hypotheses."""


def get_anthropic():
    key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not key:
        st.error("ANTHROPIC_API_KEY not set in Streamlit secrets.")
        st.stop()
    return anthropic.Anthropic(api_key=key)


def generate_hypotheses(ctx, research, client):
    research_block = "\n\n".join(f"### {k}\n{v}" for k, v in research.items())
    prompt = f"""Client context:
- Company: {ctx['client_name']}
- Product: {ctx['product_oneliner']}
- Value prop: {ctx['value_prop']}
- ICP roles: {ctx['icp_roles']}
- Company size: {ctx['company_size']}
- Geography: {ctx['geography']}
- Vertical: {ctx['vertical']}
- Problem solved: {ctx['problem_solved']}
- Win cases: {ctx.get('win_cases', 'None provided')}
- Key numbers: {ctx.get('key_numbers', 'None provided')}

Market research:
{research_block}

Generate the hypothesis set."""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=HYPOTHESIS_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)["hypotheses"]


def format_hypothesis_set(ctx, hypotheses):
    lines = [f"# Hypothesis Set — {ctx['vertical']}", ""]
    for h in hypotheses:
        lines += [
            f"## #{h['number']} {h['name']}",
            h["description"],
            f"**Best fit:** {h['best_fit']}",
            f"**Search angle:** {h['search_angle']}",
            "",
        ]
    return "\n".join(lines)


st.title("Hypothesis Set")
st.caption("Campaign angles generated from client context + market research.")

ctx = st.session_state.get("client_ctx", {})
research = st.session_state.get("research", None)

if not ctx:
    st.warning("No client brief found. Fill in **Client Brief** first.")
    st.stop()

if not research:
    st.warning("No research found. Run **Market Research** first.")
    st.stop()

st.info(f"Client: **{ctx['client_name']}** — Vertical: **{ctx['vertical']}**")

hypotheses = st.session_state.get("hypotheses", None)

if not hypotheses:
    if st.button("Generate Hypotheses", type="primary", use_container_width=True):
        with st.spinner("Generating hypotheses with Claude..."):
            try:
                client = get_anthropic()
                hypotheses = generate_hypotheses(ctx, research, client)
                st.session_state.hypotheses = hypotheses
                st.rerun()
            except Exception as e:
                st.error(f"Hypothesis generation failed: {e}")
else:
    for h in hypotheses:
        with st.expander(f"#{h['number']} — {h['name']}", expanded=True):
            st.markdown(h["description"])
            st.caption(f"**Best fit:** {h['best_fit']}")
            st.caption(f"**Search angle:** {h['search_angle']}")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Regenerate", use_container_width=True):
            st.session_state.hypotheses = None
            st.rerun()
    with col2:
        st.download_button(
            "Download hypothesis_set.md",
            data=format_hypothesis_set(ctx, hypotheses),
            file_name=f"{ctx['client_name'].lower().replace(' ', '_')}_hypotheses.md",
            mime="text/markdown",
            use_container_width=True,
        )
