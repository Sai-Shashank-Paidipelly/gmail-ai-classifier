# label_emails.py

from gmail_service import get_gmail_service
from email_classifier import classify_email  # Your existing function
import base64
import email


def get_or_create_label(service, label_name):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"].lower() == label_name.lower():
            return label["id"]

    label_obj = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    new_label = service.users().labels().create(userId="me", body=label_obj).execute()
    return new_label["id"]


def apply_label(service, msg_id, label_id):
    service.users().messages().modify(
        userId="me", id=msg_id, body={"addLabelIds": [label_id]}
    ).execute()


def main():
    service = get_gmail_service()
    messages = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["INBOX"], maxResults=5)
        .execute()
        .get("messages", [])
    )

    for message in messages:
        msg_id = message["id"]
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=msg_id, format="full")
            .execute()
        )
        headers = msg["payload"]["headers"]

        subject = next(
            (h["value"] for h in headers if h["name"].lower() == "subject"),
            "(No Subject)",
        )
        sender = next(
            (h["value"] for h in headers if h["name"].lower() == "from"), "(No Sender)"
        )

        snippet = msg.get("snippet", "")
        ai_category = classify_email(subject, snippet)

        print(f"Classified: {subject} → {ai_category}")

        label_id = get_or_create_label(service, ai_category)
        apply_label(service, msg_id, label_id)


if __name__ == "__main__":
    main()
