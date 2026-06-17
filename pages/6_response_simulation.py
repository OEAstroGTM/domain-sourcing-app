import streamlit as st
import anthropic

SIMULATION_SYSTEM = """You are simulating a real B2B prospect reading a cold email. Your job is to be brutally honest — not polite.

Given the prospect's role, company, and the email copy, produce a structured roast in this exact format:

## Emotional Reaction (2 seconds)
**Subject line gut feel:** [what they think in 0.5 seconds]
**First sentence gut feel:** [do they keep reading or move on?]
**Overall vibe:** [feels like spam / feels like a human / feels like someone who gets my world]
**Immediate red flags:** [anything that triggers delete instinct, or "None"]

## Business Evaluation (10 seconds)
**Does this hit my KPIs?** [Yes/No — which KPI specifically]
**Priority level:** [Would I deal with this today / this week / this quarter / never]
**Bridge quality:** [How strong is the connection between my pain and their solution]
**Credibility check:** [Do I believe this person/company can deliver]
**Effort-to-value ratio:** [Is the CTA worth my time]

## Risk Flags
| Flag | Location | Severity | Issue |
|------|----------|----------|-------|
[Fill table — flag types: spam trigger, wrong pain, weak bridge, bad personalization, CTA mismatch, tone clash, scraping tell, length violation]

## Verdict
**Would they reply?** Yes / Maybe / No
**Reasoning:** [1-2 sentences — the real reason, not a polite version]

## Ranked Changes
[Top 3 most impactful changes — Current text → Problem → Rewrite]

## Rewritten Email
[Full email with all changes applied]

Be specific to this person's role. Never invent facts — reason from the title and company type if you don't have data. The emotional reaction is primary: most cold emails are killed in 2 seconds."""


def get_anthropic():
    key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not key:
        st.error("ANTHROPIC_API_KEY not set in Streamlit secrets.")
        st.stop()
    return anthropic.Anthropic(api_key=key)


st.title("Response Simulation")
st.caption("Simulate a real prospect reading your email. Gets a skeptical buyer roast — emotional reaction first, business case second.")

ctx = st.session_state.get("client_ctx", {})

col1, col2 = st.columns(2)
with col1:
    prospect_name = st.text_input("Prospect first name *", placeholder="e.g. Sarah")
    prospect_title = st.text_input("Job title *", placeholder="e.g. VP of Operations")
with col2:
    prospect_company = st.text_input("Company *", placeholder="e.g. Aviva")
    company_size = st.text_input("Company size / type", placeholder="e.g. 1,200 employees, UK insurer")

extra_context = st.text_input(
    "Any extra context (optional)",
    placeholder="e.g. Recently expanded to US, hiring 3 ops managers, uses Salesforce"
)

email_copy = st.text_area("Email copy to roast *", height=250, placeholder="Subject: ...\n\nBody...")

if st.button("Roast This Email", type="primary", use_container_width=True):
    if not all([prospect_name, prospect_title, prospect_company, email_copy]):
        st.error("Fill in prospect name, title, company, and the email copy.")
    else:
        prompt_parts = [
            f"Prospect: {prospect_name}, {prospect_title} at {prospect_company}",
        ]
        if company_size:
            prompt_parts.append(f"Company context: {company_size}")
        if extra_context:
            prompt_parts.append(f"Additional context: {extra_context}")
        if ctx:
            prompt_parts.append(
                f"\nClient sending this email: {ctx.get('client_name', '')} — {ctx.get('product_oneliner', '')}"
            )
        prompt_parts.append(f"\nEmail copy:\n{email_copy}")

        prompt = "\n".join(prompt_parts)

        with st.spinner(f"Simulating {prospect_name}'s reaction..."):
            client = get_anthropic()
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2500,
                system=SIMULATION_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            result = msg.content[0].text.strip()

        # Show verdict prominently
        if "Would they reply?** Yes" in result:
            st.success("Verdict: YES — they'd reply")
        elif "Would they reply?** Maybe" in result:
            st.warning("Verdict: MAYBE")
        else:
            st.error("Verdict: NO — they'd delete it")

        st.markdown(result)

        st.download_button(
            "Download simulation.md",
            data=f"# Response Simulation — {prospect_name} at {prospect_company}\n\n{result}",
            file_name=f"simulation_{prospect_name.lower()}_{prospect_company.lower().replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True,
        )
