import os
import ssl
import email
from dotenv import load_dotenv
from imapclient import IMAPClient
import openai

# Load environment variables
load_dotenv()
EMAIL = os.getenv("EMAIL_ADDRESS")
PASSWORD = os.getenv("EMAIL_PASSWORD")
openai.api_key = os.getenv("OPENAI_API_KEY")


# Connect to Gmail via IMAP and fetch emails
def fetch_emails(max_emails=100):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    with IMAPClient("imap.gmail.com", ssl_context=ssl_context) as client:
        client.login(EMAIL, PASSWORD)
        client.select_folder("INBOX", readonly=True)

        messages = client.search(["NOT", "DELETED"])
        latest = messages[-max_emails:]

        email_data = []

        for uid in reversed(latest):
            raw_message = client.fetch([uid], ["RFC822"])[uid][b"RFC822"]
            msg = email.message_from_bytes(raw_message)
            subject = msg["subject"]
            from_ = msg["from"]
            snippet = ""

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            snippet = payload.decode(errors="ignore")[:300]
                            break

                # Fallback if no plain text was found
                if not snippet:
                    for part in msg.walk():
                        if part.get_content_type() == "text/html":
                            payload = part.get_payload(decode=True)
                            if payload:
                                snippet = payload.decode(errors="ignore")[:300]
                                break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    snippet = payload.decode(errors="ignore")[:300]
                else:
                    snippet = ""

            email_data.append(
                {
                    "subject": subject,
                    "from": from_,
                    "snippet": snippet,
                }
            )

        return email_data


# Classify email with OpenAI
def classify_email(subject, snippet):
    prompt = f"""
You are an AI email assistant. Based on the subject and body of the email, classify the email into one of the following categories:

Categories:
- Sports
- Entertainment
- Job Applications
- Conferences
- Promotions
- Work
- Other

Examples:
1. "ESPN Weekly Highlights" → Sports
2. "AMC Movie Times" → Entertainment
3. "Application for Software Engineer Role" → Job Applications
4. "Invitation: AI Research Conference 2024" → Conferences
5. "30% Off New Headphones!" → Promotions
6. "Project deadline and updates" → Work
8. "Data Analyst Skills that matter in 2025" → Promotions
9. "Practice coding with interviews" →  Promotions
10. "Can you solve this problem?" →  Promotions

Classify the following:

Subject: {subject}
Body: {snippet}

Return only the category name.
"""
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt.strip()}]
    )
    return response.choices[0].message.content.strip()
