"""
Expo Push Notification helper for GateKeeper/PA Lite.
Sends push notifications via Expo's push API (free, no account needed).
"""
import json
import urllib.request
import urllib.error
import sqlite3

EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'


def _get_tokens(db, user_ids: list) -> list:
    """Fetch all push tokens for a list of user_ids."""
    if not user_ids:
        return []
    placeholders = ','.join('?' * len(user_ids))
    rows = db.execute(
        f"SELECT token FROM push_tokens WHERE user_id IN ({placeholders})",
        user_ids
    ).fetchall()
    return [r[0] for r in rows if r[0] and r[0].startswith('ExponentPushToken')]


def _get_tokens_for_apartment(db, apartment_id: str) -> list:
    """Get push tokens for all residents of an apartment."""
    rows = db.execute(
        "SELECT DISTINCT r.user_id FROM residents r WHERE r.apartment_id=? AND r.status='active'",
        (apartment_id,)
    ).fetchall()
    user_ids = [r[0] for r in rows]
    return _get_tokens(db, user_ids)


def _get_tokens_for_society(db, society_id: str) -> list:
    """Get push tokens for all residents in a society."""
    rows = db.execute(
        """SELECT DISTINCT pt.token FROM push_tokens pt
           JOIN residents r ON r.user_id = pt.user_id
           WHERE r.society_id=? AND r.status='active'
           AND pt.token LIKE 'ExponentPushToken%'""",
        (society_id,)
    ).fetchall()
    return [r[0] for r in rows]


def _get_tokens_for_user(db, user_id: str) -> list:
    """Get push tokens for a specific user."""
    return _get_tokens(db, [user_id])


def send_push(tokens: list, title: str, body: str, data: dict = None):
    """
    Send push notification to a list of Expo push tokens.
    Batches up to 100 per request (Expo limit).
    Silently ignores errors so a push failure never breaks the API response.
    """
    if not tokens:
        return

    messages = [
        {
            'to': token,
            'title': title,
            'body': body,
            'sound': 'default',
            'data': data or {},
            'priority': 'high',
            'channelId': 'default',
        }
        for token in tokens
    ]

    # Batch into chunks of 100
    for i in range(0, len(messages), 100):
        batch = messages[i:i + 100]
        try:
            payload = json.dumps(batch).encode('utf-8')
            req = urllib.request.Request(
                EXPO_PUSH_URL,
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip, deflate',
                }
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            # Never let push failure break the main response
            print(f'[push] Failed to send batch: {e}')


# ─── Trigger helpers ─────────────────────────────────────────────────────────────

def notify_visitor_arrived(db, apartment_id: str, visitor_name: str, visitor_type: str, entry_id: str):
    """Notify residents of an apartment that a visitor is at the gate."""
    tokens = _get_tokens_for_apartment(db, apartment_id)
    type_label = visitor_type.replace('_', ' ').title()
    send_push(
        tokens,
        title=f'🔔 {type_label} at the Gate',
        body=f'{visitor_name} is at your gate. Tap to approve or reject.',
        data={'screen': 'Visitors', 'entryId': entry_id, 'type': 'visitor_arrived'},
    )


def notify_visitor_decision(db, user_id: str, visitor_name: str, approved: bool, entry_id: str):
    """Notify the resident that their visitor approval was acted on (confirmation echo)."""
    # This is mainly useful for multi-resident apartments where one resident acts
    tokens = _get_tokens_for_user(db, user_id)
    if approved:
        send_push(tokens,
            title='✅ Visitor Approved',
            body=f'{visitor_name} has been allowed entry.',
            data={'screen': 'Visitors', 'entryId': entry_id, 'type': 'visitor_approved'},
        )
    else:
        send_push(tokens,
            title='❌ Visitor Rejected',
            body=f'Entry for {visitor_name} was rejected.',
            data={'screen': 'Visitors', 'entryId': entry_id, 'type': 'visitor_rejected'},
        )


def notify_news_published(db, society_id: str, title: str, news_id: str):
    """Notify all residents in a society about a new news post."""
    tokens = _get_tokens_for_society(db, society_id)
    send_push(
        tokens,
        title='📰 Society News',
        body=title,
        data={'screen': 'News', 'newsId': news_id, 'type': 'news'},
    )


def notify_booking_confirmed(db, user_id: str, space_name: str, booking_date: str, booking_id: str):
    """Notify a resident that their booking is confirmed after payment."""
    tokens = _get_tokens_for_user(db, user_id)
    send_push(
        tokens,
        title='✅ Booking Confirmed',
        body=f'{space_name} on {booking_date} is confirmed.',
        data={'screen': 'Bookings', 'bookingId': booking_id, 'type': 'booking_confirmed'},
    )
