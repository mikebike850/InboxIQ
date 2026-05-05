import streamlit as st
import pandas as pd
from views.db import get_db

STATUSES = ["Applied", "Phone Screen", "Technical", "Interview", "Offer", "Rejected", "Withdrawn"]


@st.cache_data(ttl=300)
def load_kpi_data():
    conn = get_db()

    email_total = conn.execute('SELECT COUNT(*) FROM emails').fetchone()[0]

    classified_total = conn.execute(
        'SELECT COUNT(DISTINCT email_id) FROM classifications'
    ).fetchone()[0]

    needs_response = conn.execute('''
        SELECT COUNT(*) FROM emails e
        JOIN classifications c ON e.id = c.email_id
        WHERE c.category = 'Needs Response' AND e.is_read = 0
    ''').fetchone()[0]

    app_status_rows = conn.execute(
        'SELECT status, COUNT(*) AS count FROM job_applications GROUP BY status'
    ).fetchall()

    category_rows = conn.execute('''
        SELECT category, COUNT(*) AS count
        FROM classifications
        GROUP BY category
        ORDER BY count DESC
    ''').fetchall()

    urgency_rows = conn.execute('''
        SELECT urgency, COUNT(*) AS count
        FROM classifications
        GROUP BY urgency
    ''').fetchall()

    app_time_rows = conn.execute('''
        SELECT date_applied, COUNT(*) AS count
        FROM job_applications
        WHERE date_applied IS NOT NULL AND date_applied != ''
        GROUP BY date_applied
        ORDER BY date_applied
    ''').fetchall()

    recruiter_rows = conn.execute('''
        SELECT company_name, COUNT(*) AS emails
        FROM classifications
        WHERE category = 'Recruiter' AND company_name IS NOT NULL
        GROUP BY company_name
        ORDER BY emails DESC
        LIMIT 10
    ''').fetchall()

    mailing_list_count = conn.execute(
        "SELECT COUNT(*) FROM classifications WHERE is_mailing_list = 1"
    ).fetchone()[0]

    conn.close()

    return {
        'email_total': email_total,
        'classified_total': classified_total,
        'needs_response': needs_response,
        'app_by_status': [dict(r) for r in app_status_rows],
        'categories': [dict(r) for r in category_rows],
        'urgencies': [dict(r) for r in urgency_rows],
        'app_over_time': [dict(r) for r in app_time_rows],
        'top_recruiters': [dict(r) for r in recruiter_rows],
        'mailing_list_count': mailing_list_count,
    }


def _derive(data):
    counts = {r['status']: r['count'] for r in data['app_by_status']}
    total = sum(counts.values())

    active = sum(counts.get(s, 0) for s in ["Applied", "Phone Screen", "Technical", "Interview"])

    responded = sum(
        counts.get(s, 0)
        for s in ["Phone Screen", "Technical", "Interview", "Offer", "Rejected"]
    )
    response_rate = round(responded / total * 100) if total else 0

    return {
        'total_apps': total,
        'active_apps': active,
        'response_rate': response_rate,
        'offers': counts.get("Offer", 0),
    }


def render():
    st.title("KPI Dashboard")

    data = load_kpi_data()
    kpis = _derive(data)

    # ── Top-level metrics ─────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Emails Ingested", f"{data['email_total']:,}")
    m2.metric("Needs Response", data['needs_response'], help="Unread emails needing a reply")
    m3.metric("Applications", kpis['total_apps'])
    m4.metric("Active Pipeline", kpis['active_apps'])
    m5.metric("Response Rate", f"{kpis['response_rate']}%", help="% of applications that advanced past Applied")

    st.markdown("---")

    # ── Pipeline funnel & Inbox category ─────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Pipeline by Stage")
        counts = {r['status']: r['count'] for r in data['app_by_status']}
        funnel_df = pd.DataFrame(
            {'Applications': {s: counts.get(s, 0) for s in STATUSES}}
        )
        st.bar_chart(funnel_df)

    with col_right:
        st.subheader("Inbox by Category")
        if data['categories']:
            cat_df = (
                pd.DataFrame(data['categories'])
                .set_index('category')
                .rename(columns={'count': 'Emails'})
            )
            st.bar_chart(cat_df)
        else:
            st.info("No classifications yet.")

    st.markdown("---")

    # ── Applications over time ────────────────────────────────────────────────
    st.subheader("Applications Over Time")
    if data['app_over_time']:
        time_df = pd.DataFrame(data['app_over_time'])
        time_df['date_applied'] = pd.to_datetime(time_df['date_applied'], errors='coerce')
        time_df = time_df.dropna(subset=['date_applied']).set_index('date_applied').sort_index()

        if len(time_df) >= 2:
            weekly = time_df.resample('W').sum()
            weekly.index = weekly.index.strftime('%b %d')
            st.line_chart(weekly.rename(columns={'count': 'Applications'}))
        else:
            # Not enough points for a meaningful line — fall back to bar
            time_df.index = time_df.index.strftime('%b %d')
            st.bar_chart(time_df.rename(columns={'count': 'Applications'}))
    else:
        st.info("No application dates recorded yet. Add applications with dates to see the trend.")

    st.markdown("---")

    # ── Urgency breakdown & Top recruiters ────────────────────────────────────
    col_urg, col_rec = st.columns(2)

    with col_urg:
        st.subheader("Email Urgency")
        urgency_map = {r['urgency']: r['count'] for r in data['urgencies']}
        total_classified = sum(urgency_map.values()) or 1
        for level in ['High', 'Medium', 'Low']:
            count = urgency_map.get(level, 0)
            pct = round(count / total_classified * 100)
            st.metric(f"{level} Priority", count, f"{pct}% of classified")

        st.markdown("---")
        st.caption(
            f"**{data['classified_total']:,}** emails classified &nbsp;·&nbsp; "
            f"**{data['mailing_list_count']:,}** mailing list"
        )

    with col_rec:
        st.subheader("Top Recruiter Companies")
        if data['top_recruiters']:
            rec_df = (
                pd.DataFrame(data['top_recruiters'])
                .set_index('company_name')
                .rename(columns={'emails': 'Emails'})
            )
            st.bar_chart(rec_df)
        else:
            st.info("No recruiter emails classified yet.")
