import streamlit as st

st.set_page_config(
    page_title="Leads That Show — Ops",
    page_icon="🚀",
    layout="centered",
)

domain_sourcing = st.Page(
    "pages/domain_sourcing.py",
    title="Domain Sourcing",
    icon="🌐",
)
client_onboarding = st.Page(
    "pages/client_onboarding.py",
    title="Client Onboarding",
    icon="📋",
)

pg = st.navigation([domain_sourcing, client_onboarding])
pg.run()
