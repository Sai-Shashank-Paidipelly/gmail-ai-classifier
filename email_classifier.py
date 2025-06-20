import os
import ssl
import email
import re
from dotenv import load_dotenv
from imapclient import IMAPClient
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


def fetch_emails(max_emails=15):
    try:
        service = get_gmail_service()

        # Get categories dynamically from the prompt file
        categories = get_categories_from_prompt()
        print(f"Looking for emails not categorized with: {categories}")

        # First, get all available labels to see their actual IDs
        labels_response = service.users().labels().list(userId="me").execute()
        all_labels = labels_response.get("labels", [])

        # Print all labels for debugging
        print("Available labels in Gmail:")
        for label in all_labels:
            print(f"  - {label['name']} (ID: {label['id']})")

        # Map our category names to actual label IDs
        category_label_ids = []
        for category in categories:
            for label in all_labels:
                if category.lower() == label["name"].lower():
                    category_label_ids.append(label["id"])

        print(f"Category label IDs to exclude: {category_label_ids}")

        # Fetch messages from the Primary category
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                q="category:primary",
                maxResults=max_emails * 2,  # Fetch more to account for filtering
            )
            .execute()
        )

        messages = response.get("messages", [])
        print(f"Found {len(messages)} messages in primary category")
        email_data = []
        skipped_count = 0

        for message in messages:
            if len(email_data) >= max_emails:
                break

            msg_id = message["id"]

            # Get full message details
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )

            # Check if the email has any of our category labels
            msg_labels = msg.get("labelIds", [])
            print(f"Email ID {msg_id} has labels: {msg_labels}")

            # Skip if the email has any of our category labels
            if any(label_id in msg_labels for label_id in category_label_ids):
                print(f"Skipping email with ID {msg_id} - already categorized")
                skipped_count += 1
                continue

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
                {
                    "id": msg_id,
                    "subject": subject,
                    "from": sender,
                    "snippet": snippet,
                }
            )

        print(
            f"Processed {len(email_data)} emails, skipped {skipped_count} already categorized emails"
        )
        return email_data

    except Exception as e:
        print(f"[ERROR] Failed to fetch emails via Gmail API: {e}")
        traceback.print_exc()  # Print full traceback for debugging
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
