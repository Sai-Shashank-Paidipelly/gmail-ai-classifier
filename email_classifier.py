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
