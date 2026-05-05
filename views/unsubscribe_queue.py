import re
import streamlit as st
from datetime import datetime
from views.db import get_db


def _extract_domain(sender):
    match = re.search(r'<([^>]+)>', sender)
    email = match.group(1) if match else sender.strip()
    if '@' in email:
        return email.split('@')[1].lower().strip('>')
    return ''


def _safe_key(sender):
    return re.sub(r'\W+', '_', sender)[:40]


@st.cache_data(ttl=60)
def load_mailing_list_senders():
    conn = get_db()

    sender_rows = conn.execute('''
        SELECT
            e.sender,
            COUNT(DISTINCT e.id) AS email_count,
            MIN(e.timestamp)     AS first_seen,
            MAX(e.timestamp)     AS last_seen
        FROM emails e
        INNER JOIN classifications c ON e.id = c.email_id
        WHERE c.is_mailing_list = 1
        GROUP BY e.sender
        ORDER BY email_count DESC
    ''').fetchall()

    sub_rows = conn.execute('SELECT sender, unsubscribed FROM subscriptions').fetchall()
    sub_map = {r['sender']: r['unsubscribed'] for r in sub_rows}

    conn.close()

    result = []
    for r in sender_rows:
        d = dict(r)
        d['unsubscribed'] = bool(sub_map.get(r['sender'], 0))
        d['domain'] = _extract_domain(r['sender'])
        result.append(d)
    return result


def _set_unsubscribed(sender, value: int):
    conn = get_db()
    existing = conn.execute(
        'SELECT id FROM subscriptions WHERE sender = ?', (sender,)
    ).fetchone()
    if existing:
        conn.execute(
            'UPDATE subscriptions SET unsubscribed = ? WHERE sender = ?',
            (value, sender)
        )
    else:
        conn.execute(
            '''INSERT INTO subscriptions (sender, domain, first_seen, email_count, unsubscribed)
               VALUES (?, ?, CURRENT_TIMESTAMP, 0, ?)''',
            (sender, _extract_domain(sender), value)
        )
    conn.commit()
    conn.close()
    load_mailing_list_senders.clear()


def render():
    st.title("Unsubscribe Queue")
    st.caption("Mailing lists and newsletters detected in your inbox")

    senders = load_mailing_list_senders()

    if not senders:
        st.info("No mailing lists detected yet. Run the classifier to identify subscriptions.")
        return

    # ── Metrics ───────────────────────────────────────────────────────────────
    total = len(senders)
    n_unsub = sum(1 for s in senders if s['unsubscribed'])
    n_active = total - n_unsub

    m1, m2, m3 = st.columns(3)
    m1.metric("Detected", total)
    m2.metric("Still Active", n_active)
    m3.metric("Marked Done", n_unsub)

    st.markdown("---")

    # ── Filter + sort controls ────────────────────────────────────────────────
    ctrl_left, ctrl_right = st.columns([3, 2])
    with ctrl_left:
        show = st.radio(
            "Show",
            ["Active only", "All", "Done only"],
            horizontal=True,
            index=0,
        )
    with ctrl_right:
        sort_by = st.selectbox(
            "Sort by",
            ["Most emails", "Most recent", "Oldest"],
            index=0,
            label_visibility="collapsed",
        )

    # Apply show filter
    if show == "Active only":
        display = [s for s in senders if not s['unsubscribed']]
    elif show == "Done only":
        display = [s for s in senders if s['unsubscribed']]
    else:
        display = list(senders)

    # Apply sort
    if sort_by == "Most recent":
        display.sort(key=lambda r: r['last_seen'] or 0, reverse=True)
    elif sort_by == "Oldest":
        display.sort(key=lambda r: r['first_seen'] or 0)
    # "Most emails" is the default from the query; no re-sort needed

    st.caption(f"{len(display)} sender{'s' if len(display) != 1 else ''}")

    if not display:
        st.info("Nothing to show for this filter.")
        return

    # ── Sender cards ──────────────────────────────────────────────────────────
    for row in display:
        with st.container(border=True):
            col_main, col_action = st.columns([5, 1])

            with col_main:
                sender_label = row['sender']
                if row['unsubscribed']:
                    st.markdown(f"~~{sender_label}~~")
                else:
                    st.markdown(f"**{sender_label}**")

                parts = [f"{row['email_count']} email{'s' if row['email_count'] != 1 else ''}"]
                if row['domain']:
                    parts.append(row['domain'])
                if row['first_seen']:
                    first = datetime.fromtimestamp(row['first_seen']).strftime('%b %Y')
                    parts.append(f"since {first}")
                if row['last_seen']:
                    last = datetime.fromtimestamp(row['last_seen']).strftime('%b %d')
                    parts.append(f"last {last}")
                st.caption("  ·  ".join(parts))

            with col_action:
                key = _safe_key(row['sender'])
                if row['unsubscribed']:
                    st.caption("Done")
                    if st.button("Undo", key=f"undo_{key}"):
                        _set_unsubscribed(row['sender'], 0)
                        st.rerun()
                else:
                    if st.button("Unsubscribe", key=f"unsub_{key}"):
                        _set_unsubscribed(row['sender'], 1)
                        st.rerun()
