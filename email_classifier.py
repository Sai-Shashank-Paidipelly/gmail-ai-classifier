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
def fetch_emails(max_emails=5):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    with IMAPClient('imap.gmail.com', ssl_context=ssl_context) as client:
        client.login(EMAIL, PASSWORD)
        client.select_folder('INBOX', readonly=True)

        messages = client.search(['NOT', 'DELETED'])
        latest = messages[-max_emails:]

        email_data = []

        for uid in reversed(latest):
            raw_message = client.fetch([uid], ['RFC822'])[uid][b'RFC822']
            msg = email.message_from_bytes(raw_message)
            subject = msg['subject']
            from_ = msg['from']
            snippet = ""

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        snippet = part.get_payload(decode=True).decode(errors='ignore')[:300]
                        break
            else:
                snippet = msg.get_payload(decode=True).decode(errors='ignore')[:300]

            email_data.append({
                'subject': subject,
                'from': from_,
                'snippet': snippet,
            })

        return email_data

# Classify email with OpenAI
def classify_email(subject, snippet):
    prompt = f"""
    Subject: {subject}
    Body: {snippet}

    Classify this email as "Important" or "Promotional". Return only one word.
    """
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt.strip()}]
    )
    return response.choices[0].message.content.strip()


