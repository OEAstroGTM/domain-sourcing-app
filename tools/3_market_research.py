import streamlit as st
import anthropic

RESEARCH_SYSTEM = """You are a B2B market analyst. Research the target vertical's pain points
with depth and specificity. Use concrete numbers, workflow descriptions, tool names, and
failure modes. No generalities. No fluff. Each section should teach something actionable."""


def get_anthropic():
    key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not key:
        st.error("ANTHROPIC_API_KEY not set in Streamlit secrets.")
        st.stop()
    return anthropic.Anthropic(api_key=key)


def run_query(label: str, prompt: str, client: anthropic.Anthropic) -> str:
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=RESEARCH_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


st.title("Market Research")
st.caption("Claude maps pain points in the target vertical. Results feed into Hypothesis Set.")

ctx = st.session_state.get("client_ctx", {})
if not ctx:
    st.warning("No client brief found. Fill in **Client Brief** first.")
    st.stop()

st.info(f"Client: **{ctx['client_name']}** — Vertical: **{ctx['vertical']}**")

if st.button("Run Market Research", type="primary", use_container_width=True):
    st.session_state.research = {}
    st.rerun()

research = st.session_state.get("research", None)

if research is None:
    st.caption("Hit the button above to run research for this client.")
elif research == {}:
    client = get_anthropic()
    vertical = ctx["vertical"]
    icp_role = ctx["icp_roles"]
    problem = ctx["problem_solved"]

    queries = [
        ("Workflow pain",
         f"Describe the specific day-to-day workflow for {icp_role} at {vertical} companies "
         f"when they handle {problem}. What tools do they use? Where do those tools fail? "
         f"How long does each step take? Give concrete examples and data points, not generalities."),
        ("Tool gaps",
         f"How well do existing tools serve {vertical} companies trying to solve {problem}? "
         f"What do those tools miss? Why do companies in this space keep falling back on manual work? "
         f"What are the most common workarounds? Give specific numbers where possible."),
        ("Scaling problems",
         f"What happens when {vertical} companies try to scale {problem} beyond the early stage? "
         f"What breaks? What are the real failure modes? How do they work around it and at what cost?"),
    ]

    results = {}
    for label, query in queries:
        with st.spinner(f"Researching: {label}..."):
            try:
                result = run_query(label, query, client)
                results[label] = result
                with st.expander(f"✅ {label}", expanded=True):
                    st.markdown(result)
            except Exception as e:
                st.warning(f"'{label}' failed: {e}")
                results[label] = f"[Research failed: {e}]"

    st.session_state.research = results
    st.success("Research complete. Continue to Hypothesis Set →")

    research_md = "\n\n".join(f"### {k}\n{v}" for k, v in results.items())
    st.download_button(
        "Download research.md",
        data=f"# Market Research — {ctx['vertical']}\n\n{research_md}",
        file_name=f"{ctx['client_name'].lower().replace(' ', '_')}_research.md",
        mime="text/markdown",
        use_container_width=True,
    )

else:
    for label, text in research.items():
        with st.expander(f"✅ {label}", expanded=False):
            st.markdown(text)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Re-run Research", use_container_width=True):
            st.session_state.research = {}
            st.rerun()
    with col2:
        research_md = "\n\n".join(f"### {k}\n{v}" for k, v in research.items())
        st.download_button(
            "Download research.md",
            data=f"# Market Research — {ctx['vertical']}\n\n{research_md}",
            file_name=f"{ctx['client_name'].lower().replace(' ', '_')}_research.md",
            mime="text/markdown",
            use_container_width=True,
        )
