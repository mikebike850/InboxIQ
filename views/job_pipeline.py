import streamlit as st
from datetime import date
from views.db import get_db

STATUSES = ["Applied", "Phone Screen", "Technical", "Interview", "Offer", "Rejected", "Withdrawn"]


@st.cache_data(ttl=60)
def load_applications():
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM job_applications ORDER BY updated_at DESC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@st.cache_data(ttl=60)
def load_email_discoveries():
    conn = get_db()
    rows = conn.execute('''
        SELECT c.company_name, c.role_title, c.application_date,
               e.sender, e.subject, e.id AS email_id, e.timestamp
        FROM classifications c
        JOIN emails e ON c.email_id = e.id
        WHERE c.category IN ('Job Application', 'Recruiter')
          AND c.company_name IS NOT NULL
        ORDER BY e.timestamp DESC
        LIMIT 30
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _add_application(company, role, date_applied, status, notes, thread_id=None):
    conn = get_db()
    conn.execute(
        '''INSERT INTO job_applications (company, role, date_applied, status, notes, thread_id)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (company, role, date_applied, status, notes, thread_id)
    )
    conn.commit()
    conn.close()
    load_applications.clear()


def _update_status(app_id, new_status):
    conn = get_db()
    conn.execute(
        'UPDATE job_applications SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (new_status, app_id)
    )
    conn.commit()
    conn.close()
    load_applications.clear()


def _delete_application(app_id):
    conn = get_db()
    conn.execute('DELETE FROM job_applications WHERE id = ?', (app_id,))
    conn.commit()
    conn.close()
    load_applications.clear()


def render():
    st.title("Job Pipeline")

    apps = load_applications()

    # ── Summary metrics ───────────────────────────────────────────────────────
    by_status = {s: 0 for s in STATUSES}
    for app in apps:
        s = app.get('status', 'Applied')
        if s in by_status:
            by_status[s] += 1

    metric_cols = st.columns(len(STATUSES))
    for i, status in enumerate(STATUSES):
        metric_cols[i].metric(status, by_status[status])

    st.markdown("---")

    # ── Add Application ───────────────────────────────────────────────────────
    with st.expander("Add Application", expanded=not apps):
        with st.form("add_app_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            company = c1.text_input("Company *")
            role = c2.text_input("Role Title *")
            c3, c4 = st.columns(2)
            date_applied = c3.date_input("Date Applied", value=date.today())
            status = c4.selectbox("Status", STATUSES, index=0)
            notes = st.text_area("Notes", height=80)
            submitted = st.form_submit_button("Add Application", type="primary")

    if submitted:
        if company and role:
            _add_application(company, role, str(date_applied), status, notes)
            st.success(f"Added **{role}** at **{company}**")
            st.rerun()
        else:
            st.warning("Company and Role are required.")

    st.markdown("---")

    # ── Kanban board ──────────────────────────────────────────────────────────
    apps_by_status = {s: [] for s in STATUSES}
    for app in apps:
        s = app.get('status', 'Applied')
        target = s if s in apps_by_status else 'Applied'
        apps_by_status[target].append(app)

    if not apps:
        st.info("No applications tracked yet. Add one above or import from emails below.")
    else:
        board = st.columns(len(STATUSES))
        for i, status in enumerate(STATUSES):
            with board[i]:
                count = len(apps_by_status[status])
                st.markdown(f"**{status}** ({count})")

                for app in apps_by_status[status]:
                    with st.container(border=True):
                        st.markdown(f"**{app['company']}**")
                        st.caption(app['role'])
                        if app.get('date_applied'):
                            st.caption(f"Applied {app['date_applied']}")

                        current_idx = STATUSES.index(status)
                        new_status = st.selectbox(
                            "status",
                            STATUSES,
                            index=current_idx,
                            key=f"move_{app['id']}",
                            label_visibility="collapsed",
                        )
                        if new_status != status:
                            _update_status(app['id'], new_status)
                            st.rerun()

                        if st.button("Remove", key=f"del_{app['id']}"):
                            _delete_application(app['id'])
                            st.rerun()

    st.markdown("---")

    # ── Email discoveries ─────────────────────────────────────────────────────
    st.subheader("Discovered in Email")
    discoveries = load_email_discoveries()

    if not discoveries:
        st.info("No job-related emails found yet. Run the classifier to surface applications.")
        return

    tracked_companies = {app['company'].lower() for app in apps}

    for disc in discoveries:
        company_name = disc['company_name'] or ''
        role_title = disc['role_title'] or 'Unknown Role'
        already_tracked = company_name.lower() in tracked_companies

        label = f"{company_name} — {role_title}"
        if already_tracked:
            label += "  *(tracked)*"

        with st.expander(label):
            st.write(f"**Subject:** {disc['subject']}")
            st.write(f"**From:** {disc['sender']}")
            if disc.get('application_date'):
                st.write(f"**Application date:** {disc['application_date']}")

            if already_tracked:
                st.caption("Already in pipeline")
            else:
                if st.button("Add to Pipeline", key=f"import_{disc['email_id']}"):
                    _add_application(
                        company_name,
                        role_title,
                        disc.get('application_date') or str(date.today()),
                        'Applied',
                        f"Imported from email: {disc['subject']}",
                    )
                    st.success(f"Added **{role_title}** at **{company_name}**")
                    st.rerun()
