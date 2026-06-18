import streamlit as st
from datetime import date

st.title("Client Brief")
st.caption("Fill in client context once. Every other tool in this app reads from it.")

# Load existing context if available
existing = st.session_state.get("client_ctx", {})

with st.form("brief_form"):
    client_name = st.text_input("Client / company name *", value=existing.get("client_name", ""), placeholder="e.g. Kindred")
    client_website = st.text_input("Website", value=existing.get("client_website", ""), placeholder="e.g. kindred.ai")
    product_oneliner = st.text_input("What they do (one line) *", value=existing.get("product_oneliner", ""), placeholder="e.g. AI voice software with patented noise cancellation for enterprise contact centres")
    value_prop = st.text_area("Value prop *", value=existing.get("value_prop", ""), placeholder="e.g. Reduces agent handling time by 30% by eliminating background noise on both ends of the call", height=80)
    email_safe_vp = st.text_area("Email-safe value prop", value=existing.get("email_safe_vp", ""), placeholder="Same meaning, no jargon or banned words. Leave blank to copy value prop.", height=80)
    key_numbers = st.text_input("Key numbers / proof points", value=existing.get("key_numbers", ""), placeholder="e.g. 30% reduction in AHT, 200+ contact centres, patented in 14 countries")

    st.divider()

    vertical = st.text_input("Target vertical *", value=existing.get("vertical", ""), placeholder="e.g. Enterprise contact centres, US & UK")
    icp_roles = st.text_input("ICP job titles / roles *", value=existing.get("icp_roles", ""), placeholder="e.g. VP Operations, Head of CX, Contact Centre Director")
    company_size = st.text_input("Target company size *", value=existing.get("company_size", ""), placeholder="e.g. 200-2,000 employees")
    geography = st.text_input("Target geography *", value=existing.get("geography", ""), placeholder="e.g. United States, United Kingdom")
    problem_solved = st.text_input("Core problem we solve *", value=existing.get("problem_solved", ""), placeholder="e.g. Background noise degrading call quality and increasing handling time")

    st.divider()

    sender_name = st.text_input("Sender name", value=existing.get("sender_name", ""), placeholder="e.g. James Harper, Kindred")
    tone = st.text_input("Email tone", value=existing.get("tone", "Professional, direct. No buzzwords or fluff."))
    win_cases = st.text_area("Win cases (optional)", value=existing.get("win_cases", ""), placeholder="e.g. Deployed at TalkTalk — reduced AHT by 28% in first 90 days", height=80)

    submitted = st.form_submit_button("Save Client Brief", type="primary", use_container_width=True)

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
        st.session_state.client_ctx = {
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
        st.success(f"Brief saved for **{client_name.strip()}**. Continue to Domain Sourcing →")

        # Show downloadable brief
        brief_md = f"""# Company Context — {client_name.strip()}
Generated: {date.today().isoformat()}

## What We Do
**Product:** {product_oneliner.strip()}
**Value prop:** {value_prop.strip()}
**Email-safe VP:** {email_safe_vp.strip() or value_prop.strip()}
**Key numbers:** {key_numbers.strip() or '—'}

## Voice
**Sender:** {sender_name.strip() or client_name.strip()}
**Tone:** {tone.strip()}

## ICP
| Company size | Roles | Geographies | Problem we solve |
|---|---|---|---|
| {company_size.strip()} | {icp_roles.strip()} | {geography.strip()} | {problem_solved.strip()} |

## Win Cases
{win_cases.strip() or 'None provided yet.'}

## Do Not Contact
| Domain | Reason | Added |
|---|---|---|
| {client_website.strip() or '—'} | Client own domain | {date.today().isoformat()} |
"""
        st.download_button(
            "Download BRIEF.md",
            data=brief_md,
            file_name=f"{client_name.strip().lower().replace(' ', '_')}_BRIEF.md",
            mime="text/markdown",
            use_container_width=True,
        )
