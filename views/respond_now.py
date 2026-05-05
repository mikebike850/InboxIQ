import streamlit as st
from datetime import datetime
from views.db import get_db


@st.cache_data(ttl=60)
def load_urgent_emails():
    conn = get_db()
    rows = conn.execute('''
        SELECT e.id, e.sender, e.subject, e.snippet, e.timestamp,
               c.urgency, c.category
        FROM emails e
        JOIN classifications c ON e.id = c.email_id
        WHERE c.category = 'Needs Response'
          AND e.is_read = 0
        ORDER BY
            CASE c.urgency WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
            e.timestamp DESC
        LIMIT 50
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_read(email_id):
    conn = get_db()
    conn.execute('UPDATE emails SET is_read = 1 WHERE id = ?', (email_id,))
    conn.commit()
    conn.close()
    load_urgent_emails.clear()


def render():
    st.title("Respond Now")
    st.caption("Unread emails classified as needing a reply")

    emails = load_urgent_emails()

    if not emails:
        st.info("No unread emails need a response right now. Run the classifier to check for new mail.")
        return

    high = [e for e in emails if e['urgency'] == 'High']
    medium = [e for e in emails if e['urgency'] == 'Medium']
    low = [e for e in emails if e['urgency'] == 'Low']

    c1, c2, c3 = st.columns(3)
    c1.metric("High", len(high))
    c2.metric("Medium", len(medium))
    c3.metric("Low", len(low))

    st.markdown("---")

    for group, label in [(high, "High Priority"), (medium, "Medium Priority"), (low, "Low Priority")]:
        if not group:
            continue
        st.subheader(label)
        for em in group:
            with st.container(border=True):
                col_a, col_b = st.columns([5, 1])
                with col_a:
                    st.markdown(f"**{em['subject']}**")
                    st.caption(f"From: {em['sender']}")
                    st.write(em['snippet'])
                with col_b:
                    ts = datetime.fromtimestamp(em['timestamp']).strftime('%b %d')
                    st.caption(ts)
                    if st.button("Mark Read", key=f"read_{em['id']}"):
                        mark_read(em['id'])
                        st.rerun()
