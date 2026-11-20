import base64
from email.message import EmailMessage
from email.utils import parseaddr

from googleapiclient.discovery import build

# skip the tabs that are almost never important
DEFAULT_QUERY = "newer_than:2d -category:promotions -category:social -category:forums in:inbox"


def _service(creds):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def recent_messages(creds, query: str = DEFAULT_QUERY, limit: int = 25) -> list[dict]:
    """Newest inbox emails with sender, subject and a short preview."""
    svc = _service(creds)
    res = svc.users().messages().list(userId="me", q=query, maxResults=limit).execute()
    out = []
    for item in res.get("messages", []):
        msg = (
            svc.users()
            .messages()
            .get(userId="me", id=item["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"])
            .execute()
        )
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        name, address = parseaddr(headers.get("from", ""))
        out.append(
            {
                "id": msg["id"],
                "thread_id": msg.get("threadId", ""),
                "from": name or address,
                "from_address": address,
                "subject": headers.get("subject", "(no subject)"),
                "date": headers.get("date", ""),
                "snippet": msg.get("snippet", "")[:300],
                "unread": "UNREAD" in msg.get("labelIds", []),
            }
        )
    return out


def create_draft(creds, to: str, subject: str, body: str, thread_id: str | None = None) -> str:
    """Save a draft in Gmail. It is never sent automatically."""
    mail = EmailMessage()
    mail["To"] = to
    mail["Subject"] = subject
    mail.set_content(body)
    raw = base64.urlsafe_b64encode(mail.as_bytes()).decode()
    message = {"raw": raw}
    if thread_id:
        message["threadId"] = thread_id
    draft = _service(creds).users().drafts().create(userId="me", body={"message": message}).execute()
    return draft.get("id", "")
