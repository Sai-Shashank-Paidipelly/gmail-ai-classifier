from gmail_service import get_gmail_service
from email_classifier import classify_email


def get_or_create_label(service, label_name):
    """Retrieve label ID if it exists, or create it if not."""
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"].lower() == label_name.lower():
            return label["id"]

    label = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created_label = service.users().labels().create(userId="me", body=label).execute()
    return created_label["id"]


def label_email(service, msg_id, label_name):
    """Apply a label to a Gmail message."""
    label_id = get_or_create_label(service, label_name)
    service.users().messages().modify(
        userId="me", id=msg_id, body={"addLabelIds": [label_id]}
    ).execute()


def fetch_primary_emails(service, max_results=10):
    """Fetch messages from the Primary inbox category."""
    results = (
        service.users()
        .messages()
        .list(
            userId="me",
            labelIds=["CATEGORY_PERSONAL"],
            maxResults=max_results,
            q="category:primary",
        )
        .execute()
    )
    messages = results.get("messages", [])
    return messages


def main():
    service = get_gmail_service()

    classification_labels = [
        "Sports",
        "Entertainment",
        "Job Applications",
        "Conferences",
        "Promotions",
        "Work",
        "Other",
    ]

    # Preload label name-to-ID mapping
    label_names_to_ids = {
        name: get_or_create_label(service, name) for name in classification_labels
    }

    messages = fetch_primary_emails(service, max_results=50)

    for msg in messages:
        msg_id = msg["id"]

        # Get full message details
        msg_data = service.users().messages().get(userId="me", id=msg_id).execute()
        existing_labels = msg_data.get("labelIds", [])

        # Skip if message already has a classification label
        if any(label_id in existing_labels for label_id in label_names_to_ids.values()):
            print(f"Skipping message {msg_id}: already labeled.")
            continue

        # Extract subject and snippet
        subject = ""
        snippet = msg_data.get("snippet", "")
        headers = msg_data.get("payload", {}).get("headers", [])
        for header in headers:
            if header["name"] == "Subject":
                subject = header["value"]
                break

        # Classify and label
        category = classify_email(subject, snippet)
        print(f"Classified message {msg_id} as: {category}")
        label_email(service, msg_id, category)


if __name__ == "__main__":
    main()
