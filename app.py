# app.py
import streamlit as st

st.set_page_config(
    page_title="InboxIQ",
    page_icon="📬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar navigation
st.sidebar.title("📬 InboxIQ")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["Respond Now", "Job Pipeline", "Bills & Tickets", "Application Search", "KPI Dashboard", "Unsubscribe Queue"]
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# Route to views
if page == "Respond Now":
    from views.respond_now import render
    render()
elif page == "Job Pipeline":
    from views.job_pipeline import render
    render()
elif page == "Bills & Tickets":
    from views.bills_tickets import render
    render()
elif page == "Application Search":
    from views.app_search import render
    render()
elif page == "KPI Dashboard":
    from views.kpi_dashboard import render
    render()
elif page == "Unsubscribe Queue":
    from views.unsubscribe_queue import render
    render()
