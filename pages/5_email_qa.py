import streamlit as st
import anthropic

SPAM_GUARD_SYSTEM = """You are a cold email deliverability expert. Scan the submitted email copy against the banned word list and formatting rules below, then return a structured result.

## Tier 1 — banned single words
get, bank, credit, access, open, compare, problem, now, billing, deal, finance, financial, claims, insurance, mortgage, soon, new, performance, freedom, home, sales, medical, urgent, life, marketing, investment, diagnostics, friend, cash, invoice, extra, purchase, call, loans, million, today, free, chance

Inflected and hyphenated forms are also banned (e.g. "calls", "calling", "cash-cycle").

## Tier 2 — banned short phrases
off chance, one time, all good, following up here, last note from me here, great fit, bumping this once, just following up once, circle back, one more quick follow-up, keep this open, compare notes, appreciate the reply

## Tier 3 — promotional/pressure wording (partial list)
act now, act fast, buy now, click here, click below, free trial, limited time, money-back guarantee, guaranteed results, increase revenue, increase sales, special offer, discount, bonus, earn, giveaway, risk-free, no cost, no obligation

## Tier 4 — phishing-style language
access your account, confirm your details, verify identity, update account, final notice, immediate action required, log in now, password reset, security breach

## Formatting bans
- No em dashes (—)
- No ALL CAPS words (proper nouns and initialisms excepted)
- No multiple exclamation marks
- No "Hi {firstName}" — must be "{firstName}," with no greeting prefix
- No third-person company references ("Acme offers…" → "We offer…")

## Output format
Return EXACTLY this structure:

=== SPAM GUARD RESULT ===
Status: PASS or FAIL
Word count: <n>
Flags: <count>

--- Flagged tokens ---
<Line number and flagged token for each issue, or "None" if clean>

--- Suggested rewrite ---
<Full rewritten email if FAIL, or original copy unchanged if PASS>

--- Rewrite notes ---
<Bullet explaining each change, or "Copy is clean." if PASS>"""

SPINTAX_SYSTEM = """You are a cold email spintax expert. Apply spintax to the submitted email copy following these rules precisely.

## Spintax format
{{RANDOM|option1|option2|option3}}
- RANDOM is always all caps
- No spaces between pipes and words

## The 8 core rules

1. Every sentence's first word must be spintaxed (unless it starts with a custom variable like {{firstName}})
2. Spin every natural variation point beyond the first word — verbs, nouns, modals, short phrases. No consecutive run of more than 4-5 fixed words unless they're proper nouns or custom variables.
3. Handle articles inside the block — if options mix vowel/consonant starts, pull the article inside: {{RANDOM|a hands-on|an active}} not "a {{RANDOM|hands-on|active}}"
4. Keep blocks short — 1-3 words per option maximum
5. Minimum 2 variants per block
6. Never wrap custom variables ({{firstName}}, {{companyName}}) inside spintax blocks
7. Every word introduced via spintax must be clean (no banned spam words)
8. No em dashes in any option

## Output format
=== COLD EMAIL SPINTAX RESULT ===

Source (unchanged):
<original copy>

Spintaxed version:
<spintaxed copy>

Blocks applied: <count>
Total combinations: <product of all block sizes>

--- Sample parses (5 shown) ---
1. <fully resolved>
2. <fully resolved>
3. <fully resolved>
4. <fully resolved>
5. <fully resolved>"""


def get_anthropic():
    key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not key:
        st.error("ANTHROPIC_API_KEY not set in Streamlit secrets.")
        st.stop()
    return anthropic.Anthropic(api_key=key)


st.title("Email QA")
st.caption("Step 1: Spam Guard — scan copy for banned words. Step 2: Spintax — generate variation blocks.")

tab1, tab2 = st.tabs(["Spam Guard", "Spintax"])

with tab1:
    st.subheader("Spam Guard")
    st.caption("Paste your email copy (subject + body). Returns pass/fail + rewrite if needed.")

    copy_input = st.text_area("Email copy", height=300, placeholder="Subject: ...\n\nBody...", key="sg_input")

    if st.button("Run Spam Guard", type="primary", use_container_width=True, key="sg_btn"):
        if not copy_input.strip():
            st.error("Paste email copy first.")
        else:
            with st.spinner("Scanning copy..."):
                client = get_anthropic()
                msg = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=2000,
                    system=SPAM_GUARD_SYSTEM,
                    messages=[{"role": "user", "content": copy_input}],
                )
                result = msg.content[0].text.strip()

            passed = "Status: PASS" in result
            if passed:
                st.success("PASS — Copy is clean.")
            else:
                st.error("FAIL — Flagged tokens found. See rewrite below.")

            st.code(result, language=None)
            st.session_state.sg_result = result
            st.session_state.sg_passed = passed

    if st.session_state.get("sg_result"):
        st.download_button(
            "Download spam_guard_result.txt",
            data=st.session_state.sg_result,
            file_name="spam_guard_result.txt",
            mime="text/plain",
            use_container_width=True,
        )

with tab2:
    st.subheader("Spintax")

    if not st.session_state.get("sg_passed"):
        st.warning("Run Spam Guard first and confirm the copy passes before spintaxing.")
    else:
        st.caption("Paste your clean (spam-guard passed) copy. Claude applies spintax rules and audits 5 sample parses.")

        spintax_input = st.text_area("Clean email copy", height=300, placeholder="Subject: ...\n\nBody...", key="sx_input")
        list_size = st.number_input("List size (optional — used to calculate coverage ratio)", min_value=0, value=0, step=100)

        if st.button("Generate Spintax", type="primary", use_container_width=True, key="sx_btn"):
            if not spintax_input.strip():
                st.error("Paste email copy first.")
            else:
                prompt = spintax_input
                if list_size > 0:
                    prompt += f"\n\nList size: {list_size}"

                with st.spinner("Applying spintax and auditing combinations..."):
                    client = get_anthropic()
                    msg = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=3000,
                        system=SPINTAX_SYSTEM,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    result = msg.content[0].text.strip()

                st.code(result, language=None)
                st.session_state.sx_result = result

        if st.session_state.get("sx_result"):
            st.download_button(
                "Download spintax_result.txt",
                data=st.session_state.sx_result,
                file_name="spintax_result.txt",
                mime="text/plain",
                use_container_width=True,
            )
