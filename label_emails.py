import logging
import time
from gmail_service import get_gmail_service
from email_classifier import classify_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("label_emails")


def get_or_create_label(service, label_name):
    """Retrieve label ID if it exists, or create it if not."""
    logger.info(f"Looking for label: '{label_name}'")
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    logger.info(f"Found {len(labels)} total labels in Gmail account")

    for label in labels:
        if label["name"].lower() == label_name.lower():
            logger.info(f"Found existing label '{label_name}' with ID: {label['id']}")
            return label["id"]

    logger.info(f"Label '{label_name}' not found, creating new label")
    label = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    try:
        created_label = (
            service.users().labels().create(userId="me", body=label).execute()
        )
        logger.info(f"Created new label '{label_name}' with ID: {created_label['id']}")
        return created_label["id"]
    except Exception as e:
        logger.error(f"Error creating label '{label_name}': {e}")
        raise


def label_email(service, msg_id, label_name):
    """Apply a label to a Gmail message."""
    logger.info(f"Applying label '{label_name}' to message ID: {msg_id}")
    try:
        label_id = get_or_create_label(service, label_name)
        service.users().messages().modify(
            userId="me", id=msg_id, body={"addLabelIds": [label_id]}
        ).execute()
        logger.info(
            f"Successfully applied label '{label_name}' to message ID: {msg_id}"
        )
    except Exception as e:
        logger.error(f"Error applying label '{label_name}' to message {msg_id}: {e}")
        raise


def fetch_primary_emails(service, max_results=10, label_ids_to_exclude=None):
    """
    Fetch and return the most recent messages from the Primary inbox category that don't
    already have the specified labels. Messages are sorted by internalDate (newest first).
    """
    logger.info(
        f"Fetching up to {max_results} primary emails (excluding {len(label_ids_to_exclude or [])} labels)"
    )
    all_valid_messages = []
    page_token = None
    batch_size = 100  # Gmail's max allowed batch size
    total_messages_checked = 0

    while len(all_valid_messages) < max_results:
        logger.info(f"Fetching batch of messages (page token: {page_token or 'None'})")
        # Query to focus only on Primary inbox (filtering out other tabs)
        try:
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
            logger.info(f"Fetched {len(messages)} messages in this batch")
            total_messages_checked += len(messages)

            if not messages:
                logger.info("No more messages to fetch")
                break  # No more messages

            for msg in messages:
                if len(all_valid_messages) >= max_results * 2:
                    logger.info(
                        f"Collected enough messages ({len(all_valid_messages)}) for sorting"
                    )
                    break  # Collect more than needed to sort & slice later

                msg_id = msg["id"]
                logger.debug(f"Fetching details for message ID: {msg_id}")
                msg_data = (
                    service.users().messages().get(userId="me", id=msg_id).execute()
                )

                # Skip if message has excluded labels
                if label_ids_to_exclude:
                    msg_labels = msg_data.get("labelIds", [])
                    if any(label_id in msg_labels for label_id in label_ids_to_exclude):
                        logger.debug(f"Skipping message {msg_id} - has excluded label")
                        continue

                all_valid_messages.append(msg_data)
                logger.debug(
                    f"Added message {msg_id} to processing queue (total: {len(all_valid_messages)})"
                )

            page_token = results.get("nextPageToken")
            if not page_token:
                logger.info("No more pages of results")
                break

        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            break

    # Sort collected messages by internalDate (newest first)
    logger.info(f"Sorting {len(all_valid_messages)} collected messages by date")
    sorted_msgs = sorted(
        all_valid_messages, key=lambda m: int(m["internalDate"]), reverse=True
    )

    result_msgs = sorted_msgs[:max_results]
    logger.info(
        f"Returning {len(result_msgs)} messages (checked {total_messages_checked} total)"
    )
    return result_msgs


def delete_emails_with_label(service, label_name="Promotions", max_to_delete=10):
    """
    Deletes emails that have a custom label (e.g., 'Promotions') applied.
    """
    logger.info(
        f"Starting deletion of up to {max_to_delete} emails with label '{label_name}'"
    )
    # Step 1: Get label ID
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    label_id = None
    for label in labels:
        if label["name"].lower() == label_name.lower():
            label_id = label["id"]
            logger.info(f"Found label '{label_name}' with ID: {label_id}")
            break

    if not label_id:
        logger.warning(f"Label '{label_name}' not found. No emails will be deleted.")
        return

    deleted_count = 0
    page_token = None

    while deleted_count < max_to_delete:
        # Step 2: Find messages with the custom label
        logger.info(f"Searching for messages with label '{label_name}'")
        try:
            results = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    labelIds=[label_id],
                    maxResults=100,
                    pageToken=page_token,
                    includeSpamTrash=False,
                )
                .execute()
            )

            messages = results.get("messages", [])
            if not messages:
                logger.info("No more messages with label found.")
                break

            logger.info(f"Found {len(messages)} messages with label '{label_name}'")

            for msg in messages:
                if deleted_count >= max_to_delete:
                    break

                msg_id = msg["id"]
                try:
                    logger.info(f"Deleting message with ID: {msg_id}")
                    service.users().messages().trash(userId="me", id=msg_id).execute()
                    logger.info(f"Successfully deleted message with ID: {msg_id}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting message {msg_id}: {e}")

            page_token = results.get("nextPageToken")
            if not page_token:
                logger.info("No more pages of results")
                break

        except Exception as e:
            logger.error(f"Error searching for messages: {e}")
            break

    logger.info(f"Total messages deleted with label '{label_name}': {deleted_count}")


def main():
    logger.info("=== Starting email labeling process ===")
    start_time = time.time()

    logger.info("Getting Gmail service")
    service = get_gmail_service()

    logger.info("Starting deletion of promotional emails")
    delete_emails_with_label(service, label_name="Promotions", max_to_delete=10)

    classification_labels = [
        "Sports",
        "Entertainment",
        "Job Applications",
        "Conferences",
        "Promotions",
        "Work",
        "Other",
    ]
    logger.info(f"Using classification labels: {classification_labels}")

    # Preload label name-to-ID mapping
    logger.info("Preloading label IDs")
    label_names_to_ids = {}
    for name in classification_labels:
        try:
            label_names_to_ids[name] = get_or_create_label(service, name)
        except Exception as e:
            logger.error(f"Error preloading label '{name}': {e}")

    logger.info(f"Preloaded {len(label_names_to_ids)} label IDs")

    # Number of emails to process in one run
    emails_to_process = 10  # Increased to process more emails
    logger.info(f"Will process up to {emails_to_process} emails")

    # Fetch emails that don't have our classification labels
    logger.info("Fetching unlabeled emails")
    messages = fetch_primary_emails(
        service,
        max_results=emails_to_process,
        label_ids_to_exclude=list(label_names_to_ids.values()),
    )

    logger.info(f"Found {len(messages)} unlabeled emails to process")

    # Debug: Print the dates of the messages we're processing
    if messages:
        logger.info("Processing emails with the following details:")
        for i, msg in enumerate(messages):
            try:
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
                logger.info(f"  {i+1}. Date: {date} | Subject: {subject}")
            except Exception as e:
                logger.error(f"Error getting email details for message {i+1}: {e}")

    # Process each message
    logger.info("Starting email classification and labeling")
    for i, msg in enumerate(messages):
        msg_id = msg["id"]
        logger.info(f"Processing message {i+1}/{len(messages)} (ID: {msg_id})")

        try:
            # Get full message details
            logger.debug(f"Getting full details for message {msg_id}")
            msg_data = service.users().messages().get(userId="me", id=msg_id).execute()

            # Extract subject and snippet
            subject = ""
            snippet = msg_data.get("snippet", "")
            headers = msg_data.get("payload", {}).get("headers", [])
            for header in headers:
                if header["name"] == "Subject":
                    subject = header["value"]
                    break

            logger.info(f"Message {i+1} - Subject: '{subject}'")

            # Classify and label
            logger.info(f"Classifying message {msg_id}")
            category = classify_email(subject, snippet)
            logger.info(f"Classified message {msg_id} as: {category}")

            logger.info(f"Applying label '{category}' to message {msg_id}")
            label_email(service, msg_id, category)
            logger.info(f"Successfully processed message {i+1}/{len(messages)}")
        except Exception as e:
            logger.error(f"Error processing message {msg_id}: {e}")

    # Log completion
    elapsed_time = time.time() - start_time
    logger.info(
        f"=== Email labeling process completed in {elapsed_time:.2f} seconds ==="
    )


if __name__ == "__main__":
    main()
