from datetime import datetime
import streamlit as st
from views.db import get_db

ALL_CATEGORIES = [
    "Job Application", "Recruiter", "Bill/Fee", "Event Ticket",
    "Subscription/Mailing List", "Needs Response", "Informational", "Other"
]
ALL_URGENCIES = ["High", "Medium", "Low"]
RESULT_LIMIT = 100


@st.cache_data(ttl=60)
def load_all_classified():
    conn = get_db()
    rows = conn.execute('''
        SELECT e.id, e.thread_id, e.sender, e.subject, e.snippet,
               e.timestamp, e.is_read,
               c.category, c.urgency, c.company_name, c.role_title,
               c.application_date, c.interview_date,
               ja.status  AS pipeline_status,
               ja.company AS pipeline_company
        FROM emails e
        INNER JOIN classifications c ON e.id = c.email_id
        LEFT JOIN job_applications ja ON e.thread_id = ja.thread_id
        ORDER BY e.timestamp DESC
        LIMIT 500
    ''').fetchall()
    conn.close()

    # Deduplicate: LEFT JOIN can produce multiple rows per email when a thread
    # has more than one job_application. Keep the row that has a pipeline_status.
    seen = {}
    for r in [dict(r) for r in rows]:
        eid = r['id']
        if eid not in seen or (r['pipeline_status'] and not seen[eid]['pipeline_status']):
            seen[eid] = r
    return list(seen.values())


def _apply_filters(rows, search, categories, urgencies, job_only, unread_only):
    if job_only:
        rows = [r for r in rows if r['category'] in ('Job Application', 'Recruiter')]

    if categories and len(categories) < len(ALL_CATEGORIES):
        cat_set = set(categories)
        rows = [r for r in rows if r['category'] in cat_set]

    if urgencies and len(urgencies) < len(ALL_URGENCIES):
        urg_set = set(urgencies)
        rows = [r for r in rows if r['urgency'] in urg_set]

    if unread_only:
        rows = [r for r in rows if r['is_read'] == 0]

    if search:
        q = search.lower()
        rows = [
            r for r in rows
            if q in (r['subject'] or '').lower()
            or q in (r['sender'] or '').lower()
            or q in (r['snippet'] or '').lower()
            or q in (r['company_name'] or '').lower()
            or q in (r['role_title'] or '').lower()
        ]

    return rows


def render():
    st.title("Application Search")
    st.caption("Search and filter all classified emails")

    # ── Filters ───────────────────────────────────────────────────────────────
    search = st.text_input(
        "Search",
        placeholder="Subject, sender, company, role...",
        label_visibility="collapsed",
    )

    col_cat, col_urg, col_t1, col_t2 = st.columns([3, 2, 1.5, 1.5])
    with col_cat:
        categories = st.multiselect("Category", ALL_CATEGORIES, default=ALL_CATEGORIES)
    with col_urg:
        urgencies = st.multiselect("Urgency", ALL_URGENCIES, default=ALL_URGENCIES)
    with col_t1:
        job_only = st.toggle("Job-related only", value=False)
    with col_t2:
        unread_only = st.toggle("Unread only", value=False)

    st.markdown("---")

    # ── Data + filtering ──────────────────────────────────────────────────────
    all_rows = load_all_classified()

    # Build fallback set for company-name pipeline lookup (manually added apps)
    pipeline_cos = {
        r['pipeline_company'].lower()
        for r in all_rows
        if r['pipeline_company']
    }

    filtered = _apply_filters(all_rows, search, categories, urgencies, job_only, unread_only)
    display_rows = filtered[:RESULT_LIMIT]

    # ── Result count / empty states ───────────────────────────────────────────
    if not all_rows:
        st.info("No classified emails yet. Run the classifier to populate results.")
        return

    if not filtered:
        st.info("No results match your search or filters.")
        return

    shown = len(display_rows)
    total = len(filtered)
    suffix = "  *(limited to 100)*" if total > RESULT_LIMIT else ""
    st.caption(f"Showing **{shown}** of **{total}** results{suffix}")

    # ── Result cards ──────────────────────────────────────────────────────────
    for row in display_rows:
        with st.container(border=True):
            col_main, col_meta = st.columns([5, 1])

            with col_main:
                st.markdown(f"**{row['subject'] or '(no subject)'}**")
                st.caption(f"From: {row['sender']}")

                # Inline category + urgency badges
                st.markdown(f"`{row['category']}`  `{row['urgency']}`")

                # Extracted job metadata — only render non-null fields
                details = []
                if row['company_name']:
                    details.append(f"Company: **{row['company_name']}**")
                if row['role_title']:
                    details.append(f"Role: **{row['role_title']}**")
                if row['application_date']:
                    details.append(f"Applied: {row['application_date']}")
                if row['interview_date']:
                    details.append(f"Interview: {row['interview_date']}")
                if details:
                    st.caption("  ·  ".join(details))

                # Pipeline status indicators
                if row['pipeline_status']:
                    st.success(f"In Pipeline: {row['pipeline_status']}")
                elif row['company_name'] and row['company_name'].lower() in pipeline_cos:
                    st.info("Company tracked in pipeline")

            with col_meta:
                if row['timestamp']:
                    ts = datetime.fromtimestamp(row['timestamp']).strftime('%b %d')
                    st.caption(ts)
                if row['is_read'] == 0:
                    st.caption("• Unread")

            if row['snippet']:
                with st.expander("Show snippet"):
                    st.write(row['snippet'])
