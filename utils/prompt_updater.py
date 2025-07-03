import os
import logging
import openai
from datetime import datetime
import re
from utils.feedback_db import (
    get_unprocessed_feedback,
    mark_feedback_as_processed,
    store_prompt_update,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("prompt_updater")

PROMPT_FILE = "email_classifier_prompt.txt"


def read_current_prompt():
    """Read the current prompt from file."""
    try:
        with open(PROMPT_FILE, "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading prompt file: {e}")
        return None


def write_updated_prompt(new_prompt):
    """Write the updated prompt to file."""
    try:
        # Create a backup of the old prompt
        current_prompt = read_current_prompt()
        if current_prompt:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(f"{PROMPT_FILE}.{timestamp}.bak", "w") as f:
                f.write(current_prompt)
            logger.info(f"Backup created: {PROMPT_FILE}.{timestamp}.bak")

        # Write the new prompt
        with open(PROMPT_FILE, "w") as f:
            f.write(new_prompt)
        logger.info(f"Updated prompt written to {PROMPT_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error writing updated prompt: {e}")
        return False


def extract_examples_from_prompt(prompt_text):
    """Extract the examples section from the prompt."""
    examples_match = re.search(r"Examples:(.*?)(?:\n\n|\Z)", prompt_text, re.DOTALL)
    if examples_match:
        return examples_match.group(1).strip()
    return ""


def extract_categories_from_prompt(prompt_text):
    """Extract the categories from the prompt."""
    categories_match = re.search(r"Categories:(.*?)(?:\n\n|\Z)", prompt_text, re.DOTALL)
    if categories_match:
        categories_section = categories_match.group(1)
        categories = [
            line.strip()[2:]
            for line in categories_section.split("\n")
            if line.strip().startswith("- ")
        ]
        return categories
    return []


def generate_improved_prompt(feedback_data, current_prompt):
    """Use OpenAI to generate an improved prompt based on feedback."""
    logger.info(
        f"Generating improved prompt based on {len(feedback_data)} feedback entries"
    )

    # Extract current examples and categories
    current_examples = extract_examples_from_prompt(current_prompt)
    current_categories = extract_categories_from_prompt(current_prompt)

    # Prepare feedback for the AI
    feedback_examples = []
    for item in feedback_data:
        if item["ai_category"] != item["user_category"]:
            feedback_examples.append(
                {
                    "subject": item["subject"],
                    "snippet": item["snippet"],
                    "ai_prediction": item["ai_category"],
                    "correct_category": item["user_category"],
                }
            )

    # Create the prompt for OpenAI
    system_prompt = """You are an expert at creating effective prompts for email classification. 
Your task is to improve a classification prompt based on feedback data where the AI made incorrect predictions.
Analyze the patterns in the misclassifications and suggest improvements to the prompt."""

    user_prompt = f"""Here is the current email classification prompt:
```
{current_prompt}
```

Here are the current categories:
{', '.join(current_categories)}

Here are examples where the AI made incorrect predictions:
{feedback_examples[:20]}  # Limit to 20 examples to avoid token limits

Based on these misclassifications, please:
1. Identify patterns in the misclassifications
2. Suggest new or modified examples to add to the prompt
3. Suggest any new categories if needed
4. Provide a complete updated prompt that maintains the same format but improves classification accuracy

The updated prompt should follow the exact same format as the original, with appropriate modifications to the examples section.
"""

    try:
        response = openai.chat.completions.create(
            model="gpt-4",  # Using GPT-4 for better reasoning
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=2000,
        )

        # Extract the updated prompt from the response
        updated_prompt = response.choices[0].message.content

        # If the response contains markdown code blocks, extract the prompt
        prompt_match = re.search(r"```(?:.*?)\n(.*?)```", updated_prompt, re.DOTALL)
        if prompt_match:
            updated_prompt = prompt_match.group(1)

        logger.info("Successfully generated improved prompt")
        return updated_prompt
    except Exception as e:
        logger.error(f"Error generating improved prompt: {e}")
        return None


def update_prompt_from_feedback(min_feedback_count=50):
    """Main function to update the prompt based on collected feedback."""
    logger.info(f"Checking for prompt updates (minimum feedback: {min_feedback_count})")

    # Get unprocessed feedback
    feedback = get_unprocessed_feedback(limit=100)

    if len(feedback) < min_feedback_count:
        logger.info(
            f"Not enough feedback for prompt update. Have {len(feedback)}, need {min_feedback_count}"
        )
        return False

    # Read current prompt
    current_prompt = read_current_prompt()
    if not current_prompt:
        logger.error("Failed to read current prompt")
        return False

    # Generate improved prompt
    improved_prompt = generate_improved_prompt(feedback, current_prompt)
    if not improved_prompt:
        logger.error("Failed to generate improved prompt")
        return False

    # Write updated prompt
    success = write_updated_prompt(improved_prompt)
    if not success:
        logger.error("Failed to write updated prompt")
        return False

    # Store prompt update history
    performance_metrics = {
        "feedback_count": len(feedback),
        "update_date": datetime.now().isoformat(),
    }
    store_prompt_update(
        current_prompt, improved_prompt, len(feedback), performance_metrics
    )

    # Mark feedback as processed
    feedback_ids = [item["id"] for item in feedback]
    mark_feedback_as_processed(feedback_ids)

    logger.info("Prompt update completed successfully")
    return True
