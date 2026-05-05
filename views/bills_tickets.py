import streamlit as st
from datetime import datetime
from views.db import get_db


@st.cache_data(ttl=60)
def load_bills():
    conn = get_db()
    rows = conn.execute('''
        SELECT e.id, e.sender, e.subject, e.snippet, e.timestamp, e.is_read,
               c.urgency, c.company_name, c.application_date, c.has_date_mention
        FROM emails e
        INNER JOIN classifications c ON e.id = c.email_id
        WHERE c.category = 'Bill/Fee'
        ORDER BY
            CASE c.urgency WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
            COALESCE(c.application_date, '9999-12-31') ASC,
            e.timestamp DESC
        LIMIT 200
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


@st.cache_data(ttl=60)
def load_tickets():
    conn = get_db()
    rows = conn.execute('''
        SELECT e.id, e.sender, e.subject, e.snippet, e.timestamp, e.is_read,
               c.company_name, c.role_title, c.application_date, c.interview_date,
               c.urgency, c.has_date_mention
        FROM emails e
        INNER JOIN classifications c ON e.id = c.email_id
        WHERE c.category = 'Event Ticket'
        ORDER BY
            COALESCE(c.interview_date, c.application_date, '9999-12-31') ASC,
            e.timestamp DESC
        LIMIT 200
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _mark_read(email_id, cache_fn):
    conn = get_db()
    conn.execute('UPDATE emails SET is_read = 1 WHERE id = ?', (email_id,))
    conn.commit()
    conn.close()
    cache_fn.clear()


def _bill_card(bill):
    with st.container(border=True):
        col_main, col_meta = st.columns([5, 1])

        with col_main:
            st.markdown(f"**{bill['subject'] or '(no subject)'}**")
            st.caption(f"From: {bill['sender']}")

            details = []
            if bill['company_name']:
                details.append(f"**{bill['company_name']}**")
            if bill['application_date']:
                details.append(f"Due: {bill['application_date']}")
            elif bill['has_date_mention']:
                details.append("Date mentioned in email")
            if details:
                st.caption("  ·  ".join(details))

            if bill['snippet']:
                with st.expander("Show snippet"):
                    st.write(bill['snippet'])

        with col_meta:
            st.markdown(f"`{bill['urgency']}`")
            if bill['timestamp']:
                st.caption(datetime.fromtimestamp(bill['timestamp']).strftime('%b %d'))
            if bill['is_read'] == 0:
                st.caption("• Unread")
                if st.button("Mark Paid", key=f"paid_{bill['id']}"):
                    _mark_read(bill['id'], load_bills)
                    st.rerun()


def _ticket_card(ticket):
    event_date = ticket['interview_date'] or ticket['application_date']

    with st.container(border=True):
        col_main, col_meta = st.columns([5, 1])

        with col_main:
            st.markdown(f"**{ticket['subject'] or '(no subject)'}**")
            st.caption(f"From: {ticket['sender']}")

            details = []
            if ticket['company_name']:
                details.append(f"**{ticket['company_name']}**")
            if ticket['role_title']:
                details.append(ticket['role_title'])
            if event_date:
                details.append(f"Date: {event_date}")
            elif ticket['has_date_mention']:
                details.append("Date mentioned in email")
            if details:
                st.caption("  ·  ".join(details))

            if ticket['snippet']:
                with st.expander("Show snippet"):
                    st.write(ticket['snippet'])

        with col_meta:
            if ticket['timestamp']:
                st.caption(datetime.fromtimestamp(ticket['timestamp']).strftime('%b %d'))
            if ticket['is_read'] == 0:
                st.caption("• Unread")
                if st.button("Mark Done", key=f"done_{ticket['id']}"):
                    _mark_read(ticket['id'], load_tickets)
                    st.rerun()


def render():
    st.title("Bills & Tickets")

    bills = load_bills()
    tickets = load_tickets()

    tab_bills, tab_tickets = st.tabs([
        f"Bills & Fees  ({len(bills)})",
        f"Event Tickets  ({len(tickets)})",
    ])

    # ── Bills tab ─────────────────────────────────────────────────────────────
    with tab_bills:
        if not bills:
            st.info("No bills or fees classified yet.")
        else:
            n_high = sum(1 for b in bills if b['urgency'] == 'High')
            n_unread = sum(1 for b in bills if b['is_read'] == 0)

            m1, m2, m3 = st.columns(3)
            m1.metric("Total", len(bills))
            m2.metric("High Priority", n_high)
            m3.metric("Unread", n_unread)

            st.markdown("---")

            unread_only = st.toggle("Unread only", value=True, key="bills_unread_toggle")
            display = [b for b in bills if b['is_read'] == 0] if unread_only else bills
            st.caption(f"{len(display)} bill{'s' if len(display) != 1 else ''}")

            for bill in display:
                _bill_card(bill)

    # ── Tickets tab ───────────────────────────────────────────────────────────
    with tab_tickets:
        if not tickets:
            st.info("No event tickets classified yet.")
        else:
            n_unread = sum(1 for t in tickets if t['is_read'] == 0)

            m1, m2 = st.columns(2)
            m1.metric("Total", len(tickets))
            m2.metric("Unread", n_unread)

            st.markdown("---")

            unread_only = st.toggle("Unread only", value=False, key="tickets_unread_toggle")
            display = [t for t in tickets if t['is_read'] == 0] if unread_only else tickets
            st.caption(f"{len(display)} ticket{'s' if len(display) != 1 else ''}")

            for ticket in display:
                _ticket_card(ticket)
