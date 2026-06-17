import streamlit as st

st.set_page_config(
    page_title="Leads That Show — Ops",
    page_icon="🚀",
    layout="centered",
)

pages = [
    st.Page("pages/1_client_brief.py",        title="Client Brief",          icon="📋"),
    st.Page("pages/2_domain_sourcing.py",      title="Domain Sourcing",       icon="🌐"),
    st.Page("pages/3_market_research.py",      title="Market Research",       icon="🔍"),
    st.Page("pages/4_hypothesis_set.py",       title="Hypothesis Set",        icon="💡"),
    st.Page("pages/5_email_qa.py",             title="Email QA",              icon="✅"),
    st.Page("pages/6_response_simulation.py",  title="Response Simulation",   icon="🎭"),
]

pg = st.navigation(pages)
pg.run()
