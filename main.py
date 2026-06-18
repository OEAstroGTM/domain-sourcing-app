import streamlit as st

st.set_page_config(
    page_title="Leads That Show — Ops",
    page_icon="🚀",
    layout="centered",
)

pages = [
    st.Page("tools/1_client_brief.py",        title="Client Brief",          icon="📋"),
    st.Page("tools/2_domain_sourcing.py",      title="Domain Sourcing",       icon="🌐"),
    st.Page("tools/3_market_research.py",      title="Market Research",       icon="🔍"),
    st.Page("tools/4_hypothesis_set.py",       title="Hypothesis Set",        icon="💡"),
    st.Page("tools/5_email_qa.py",             title="Email QA",              icon="✅"),
    st.Page("tools/6_response_simulation.py",  title="Response Simulation",   icon="🎭"),
]

pg = st.navigation(pages)
pg.run()
