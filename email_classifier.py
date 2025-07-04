import os
import ssl
import email
import re
import logging
from dotenv import load_dotenv
import openai
import traceback
from jinja2 import Template
from gmail_service import get_gmail_service
import tiktoken

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("email_classifier")

# Load environment variables
logger.info("Loading environment variables")
load_dotenv()
EMAIL = os.getenv("EMAIL_ADDRESS")
PASSWORD = os.getenv("EMAIL_PASSWORD")
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    logger.warning("OPENAI_API_KEY not found in environment variables")
else:
    logger.info("OpenAI API key loaded successfully")

# Initialize token counter
total_tokens_used = 0
total_prompt_tokens = 0
total_completion_tokens = 0


def count_tokens(text, model="gpt-3.5-turbo"):
    """Count the number of tokens in a text string."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        logger.error(f"Error counting tokens: {e}")
        return 0


def get_categories_from_prompt():
    """Extract categories from the email_classifier_prompt.txt file"""
    logger.info("Extracting categories from prompt file")
    try:
        with open("email_classifier_prompt.txt", "r") as file:
            logger.info("Reading email_classifier_prompt.txt")
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
                logger.info(f"Found {len(categories)} categories: {categories}")
                return categories
            logger.warning("No categories found in the prompt file")
            return []
    except Exception as e:
        logger.error(f"Failed to read categories from prompt file: {e}")
        logger.debug(traceback.format_exc())
        return []


# Classify email with OpenAI
def classify_email(subject, snippet):
    global total_tokens_used, total_prompt_tokens, total_completion_tokens

    logger.info(f"Classifying email - Subject: '{subject[:30]}...' (truncated)")
    try:
        # Load and render prompt
        logger.info("Loading classification prompt template")
        with open("email_classifier_prompt.txt", "r") as file:
            template = Template(file.read())
            prompt = template.render(subject=subject, snippet=snippet)
            logger.debug(f"Generated prompt: {prompt[:100]}... (truncated)")

        # Count prompt tokens
        prompt_tokens = count_tokens(prompt)
        total_prompt_tokens += prompt_tokens

        # Send to OpenAI
        logger.info("Sending request to OpenAI API")
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt.strip()}],
        )

        # Track token usage
        completion_tokens = response.usage.completion_tokens
        prompt_tokens_used = response.usage.prompt_tokens
        total_tokens = response.usage.total_tokens

        total_completion_tokens += completion_tokens
        total_tokens_used += total_tokens

        logger.info(
            f"Token usage - Prompt: {prompt_tokens_used}, Completion: {completion_tokens}, Total: {total_tokens}"
        )

        category = response.choices[0].message.content.strip()
        logger.info(f"Classification result: '{category}'")
        return category
    except Exception as e:
        logger.error(f"Failed to classify email: {e}")
        logger.debug(traceback.format_exc())
        return "Other"


def get_token_usage():
    """Return the current token usage statistics."""
    return {
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens_used,
    }
