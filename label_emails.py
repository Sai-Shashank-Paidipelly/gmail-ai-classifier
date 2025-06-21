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
    Fetch messages from the Primary inbox category that don't have specified labels.
    Continues fetching in batches until it finds enough unlabeled emails or runs out of emails.
    """
    unlabeled_messages = []
    page_token = None
    batch_size = 100  # Fetch in larger batches for efficiency

    while len(unlabeled_messages) < max_results:
        # Fetch a batch of messages - explicitly query for primary category
        # and sort by newest first
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                q="category:primary -category:promotions -category:social -category:updates -category:forums",
                maxResults=batch_size,
                pageToken=page_token,
                # Ensure we're getting the newest emails first
                includeSpamTrash=False,
            )
            .execute()
        )

        messages = results.get("messages", [])
        if not messages:
            break  # No more messages to fetch

        print(f"Fetched batch of {len(messages)} primary category messages")

        # Process each message in the batch
        for msg in messages:
            # Check if we already have enough messages
            if len(unlabeled_messages) >= max_results:
                break

            msg_id = msg["id"]

            # Get message details to check labels
            if label_ids_to_exclude:
                msg_data = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="minimal")
                    .execute()
                )

                # Skip if message has any of the excluded labels
                if any(
                    label_id in msg_data.get("labelIds", [])
                    for label_id in label_ids_to_exclude
                ):
                    continue

            # If we get here, the message doesn't have any of the excluded labels
            unlabeled_messages.append(msg)

        # Check if there are more pages of results
        page_token = results.get("nextPageToken")
        if not page_token:
            break  # No more pages

    return unlabeled_messages


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
