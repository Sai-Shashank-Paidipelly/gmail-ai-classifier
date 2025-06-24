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


def fetch_primary_emails(service, max_results=10, label_ids_to_exclude=None):
    """
    Fetch and return the most recent messages from the Primary inbox category that don't
    already have the specified labels. Messages are sorted by internalDate (newest first).
    """
    all_valid_messages = []
    page_token = None
    batch_size = 100  # Gmail's max allowed batch size

    while len(all_valid_messages) < max_results:
        # Query to focus only on Primary inbox (filtering out other tabs)
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                q="category:primary",
                maxResults=batch_size,
                pageToken=page_token,
                includeSpamTrash=False,
            )
            .execute()
        )

        messages = results.get("messages", [])
        if not messages:
            break  # No more messages

        for msg in messages:
            if len(all_valid_messages) >= max_results * 2:
                break  # Collect more than needed to sort & slice later

            msg_id = msg["id"]
            msg_data = service.users().messages().get(userId="me", id=msg_id).execute()

            # Skip if message has excluded labels
            if label_ids_to_exclude:
                if any(
                    label_id in msg_data.get("labelIds", [])
                    for label_id in label_ids_to_exclude
                ):
                    continue

            all_valid_messages.append(msg_data)

        page_token = results.get("nextPageToken")
        if not page_token:
            break

    # Sort collected messages by internalDate (newest first)
    sorted_msgs = sorted(
        all_valid_messages, key=lambda m: int(m["internalDate"]), reverse=True
    )

    return sorted_msgs[:max_results]


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

    # Number of emails to process in one run
    emails_to_process = 10  # Increased to process more emails

    # Fetch emails that don't have our classification labels
    messages = fetch_primary_emails(
        service,
        max_results=emails_to_process,
        label_ids_to_exclude=list(label_names_to_ids.values()),
    )

    print(f"Found {len(messages)} unlabeled emails to process")

    # Debug: Print the dates of the messages we're processing
    if messages:
        print("Processing emails with the following details:")
        for i, msg in enumerate(messages):
            msg_data = (
                service.users().messages().get(userId="me", id=msg["id"]).execute()
            )
            headers = msg_data.get("payload", {}).get("headers", [])
            date = next(
                (h["value"] for h in headers if h["name"].lower() == "date"),
                "Unknown date",
            )
            subject = next(
                (h["value"] for h in headers if h["name"].lower() == "subject"),
                "No subject",
            )
            print(f"  {i+1}. Date: {date} | Subject: {subject}")

    for msg in messages:
        msg_id = msg["id"]

        # Get full message details
        msg_data = service.users().messages().get(userId="me", id=msg_id).execute()

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
