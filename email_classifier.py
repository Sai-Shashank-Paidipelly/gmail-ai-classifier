import os
import ssl
import email
import re
from dotenv import load_dotenv
import openai
import traceback
from jinja2 import Template
from gmail_service import get_gmail_service

# Load environment variables
load_dotenv()
EMAIL = os.getenv("EMAIL_ADDRESS")
PASSWORD = os.getenv("EMAIL_PASSWORD")
openai.api_key = os.getenv("OPENAI_API_KEY")


def get_categories_from_prompt():
    """Extract categories from the email_classifier_prompt.txt file"""
    try:
        with open("email_classifier_prompt.txt", "r") as file:
            content = file.read()
            # Look for the Categories section and extract the categories
            categories_match = re.search(r"Categories:\s*\n((?:- .*\n)+)", content)
            if categories_match:
                categories_section = categories_match.group(1)
                # Extract each category (removing the "- " prefix)
                categories = [
                    line.strip()[2:]
                    for line in categories_section.split("\n")
                    if line.strip().startswith("- ")
                ]
                return categories
            return []
    except Exception as e:
        print(f"[ERROR] Failed to read categories from prompt file: {e}")
        return []


# Fetch emails using Gmail API
def fetch_emails(max_emails=15):
    try:
        service = get_gmail_service()
        print(f"Connected to Gmail API for {EMAIL}")

        # Get all user-created labels
        labels_response = service.users().labels().list(userId="me").execute()
        all_labels = labels_response.get("labels", [])

        # Get our categories from the prompt file
        categories = get_categories_from_prompt()
        print(f"Looking for emails not categorized with: {categories}")

        # Find label IDs that match our categories
        category_label_ids = []
        for label in all_labels:
            if any(
                category.lower() == label["name"].lower() for category in categories
            ):
                category_label_ids.append(label["id"])
                print(f"Found label: {label['name']} (ID: {label['id']})")

        # Build a query that excludes messages with our category labels
        # We'll get all messages and filter them manually since Gmail API query
        # doesn't support complex label exclusions reliably
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                maxResults=max_emails * 3,  # Get more messages to account for filtering
            )
            .execute()
        )

        messages = response.get("messages", [])
        if not messages:
            print("No messages found.")
            return []

        print(f"Found {len(messages)} messages, filtering for uncategorized ones...")

        email_data = []
        processed = 0

        for message in messages:
            if len(email_data) >= max_emails:
                break

            msg_id = message["id"]
            processed += 1

            # Get full message details
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )

            # Check if this email has any of our category labels
            msg_labels = msg.get("labelIds", [])

            # Skip if the email has any of our category labels
            if any(label_id in msg_labels for label_id in category_label_ids):
                continue

            # Extract email details
            headers = msg["payload"]["headers"]
            subject = next(
                (h["value"] for h in headers if h["name"].lower() == "subject"),
                "(No Subject)",
            )
            sender = next(
                (h["value"] for h in headers if h["name"].lower() == "from"),
                "(No Sender)",
            )
            snippet = msg.get("snippet", "")

            email_data.append(
                {"id": msg_id, "subject": subject, "from": sender, "snippet": snippet}
            )

        print(
            f"Processed {processed} messages, found {len(email_data)} uncategorized emails"
        )
        return email_data

    except Exception as e:
        print(f"Error in fetch_emails: {str(e)}")
        print(traceback.format_exc())
        return []


# Classify email with OpenAI
def classify_email(subject, snippet):
    try:
        # Load and render prompt
        with open("email_classifier_prompt.txt", "r") as file:
            template = Template(file.read())
            prompt = template.render(subject=subject, snippet=snippet)

        # Send to OpenAI
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt.strip()}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR] Failed to classify email: {e}")
        return "Other"
