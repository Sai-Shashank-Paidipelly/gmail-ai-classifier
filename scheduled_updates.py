#!/usr/bin/env python3
import logging
import time
import os
import schedule
from datetime import datetime
from utils.feedback_db import init_db, get_feedback_stats
from utils.prompt_updater import update_prompt_from_feedback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="scheduled_updates.log",
    filemode="a",
)
logger = logging.getLogger("scheduled_updates")


def check_and_update_prompt():
    """Check for feedback and update prompt if needed."""
    logger.info("Running scheduled prompt update check")

    try:
        # Initialize DB if needed
        init_db()

        # Get current stats
        stats = get_feedback_stats()
        logger.info(f"Current feedback stats: {stats}")

        # Check if we have enough incorrect classifications
        incorrect_count = stats.get("incorrect_classifications", 0)
        logger.info(f"Found {incorrect_count} incorrect classifications")

        if incorrect_count >= 20:  # Threshold for updating prompt
            logger.info(
                f"Threshold reached ({incorrect_count} incorrect classifications). Updating prompt..."
            )
            success = update_prompt_from_feedback(min_feedback_count=20)

            if success:
                logger.info("Prompt updated successfully")
            else:
                logger.warning("Prompt update failed or not enough feedback")
        else:
            logger.info(
                f"Not enough incorrect classifications ({incorrect_count}/20) for prompt update"
            )

    except Exception as e:
        logger.error(f"Error in scheduled update: {e}")


def main():
    """Main function to run the scheduler."""
    logger.info("Starting scheduled updates service")

    # Schedule the prompt update check to run daily at 2 AM
    schedule.every().day.at("02:00").do(check_and_update_prompt)

    # Also run once at startup
    logger.info("Running initial prompt update check")
    check_and_update_prompt()

    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    main()
