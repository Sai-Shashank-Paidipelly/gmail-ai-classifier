import sqlite3
import os
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("feedback_db")

DB_PATH = "feedback.db"


def init_db():
    """Initialize the feedback database if it doesn't exist."""
    logger.info("Initializing feedback database")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table for storing classification feedback
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS classification_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT UNIQUE,
        subject TEXT,
        snippet TEXT,
        ai_category TEXT,
        user_category TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_processed BOOLEAN DEFAULT 0
    )
    """
    )

    # Create table for prompt updates history
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS prompt_updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        old_prompt TEXT,
        new_prompt TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        feedback_count INTEGER,
        performance_metrics TEXT
    )
    """
    )

    conn.commit()
    conn.close()
    logger.info("Database initialization complete")


def store_feedback(message_id, subject, snippet, ai_category, user_category):
    """Store user feedback about classification."""
    logger.info(f"Storing feedback for message {message_id}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            """
        INSERT OR REPLACE INTO classification_feedback 
        (message_id, subject, snippet, ai_category, user_category, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
            (message_id, subject, snippet, ai_category, user_category, datetime.now()),
        )

        conn.commit()
        conn.close()
        logger.info(f"Feedback stored successfully for message {message_id}")
        return True
    except Exception as e:
        logger.error(f"Error storing feedback: {e}")
        return False


def get_unprocessed_feedback(limit=100):
    """Retrieve unprocessed feedback for prompt improvement."""
    logger.info("Retrieving unprocessed feedback")
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
        SELECT * FROM classification_feedback
        WHERE is_processed = 0
        ORDER BY timestamp DESC
        LIMIT ?
        """,
            (limit,),
        )

        rows = cursor.fetchall()
        feedback = [dict(row) for row in rows]
        conn.close()

        logger.info(f"Retrieved {len(feedback)} unprocessed feedback entries")
        return feedback
    except Exception as e:
        logger.error(f"Error retrieving unprocessed feedback: {e}")
        return []


def mark_feedback_as_processed(feedback_ids):
    """Mark feedback as processed after using it for prompt improvement."""
    if not feedback_ids:
        return True

    logger.info(f"Marking {len(feedback_ids)} feedback entries as processed")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        placeholders = ", ".join(["?"] * len(feedback_ids))
        cursor.execute(
            f"""
        UPDATE classification_feedback
        SET is_processed = 1
        WHERE id IN ({placeholders})
        """,
            feedback_ids,
        )

        conn.commit()
        conn.close()
        logger.info(
            f"Successfully marked {cursor.rowcount} feedback entries as processed"
        )
        return True
    except Exception as e:
        logger.error(f"Error marking feedback as processed: {e}")
        return False


def store_prompt_update(old_prompt, new_prompt, feedback_count, performance_metrics):
    """Store history of prompt updates."""
    logger.info("Storing prompt update")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            """
        INSERT INTO prompt_updates 
        (old_prompt, new_prompt, timestamp, feedback_count, performance_metrics)
        VALUES (?, ?, ?, ?, ?)
        """,
            (
                old_prompt,
                new_prompt,
                datetime.now(),
                feedback_count,
                json.dumps(performance_metrics),
            ),
        )

        conn.commit()
        conn.close()
        logger.info("Prompt update stored successfully")
        return True
    except Exception as e:
        logger.error(f"Error storing prompt update: {e}")
        return False


def get_feedback_stats():
    """Get statistics about stored feedback."""
    logger.info("Retrieving feedback statistics")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get total count
        cursor.execute("SELECT COUNT(*) FROM classification_feedback")
        total_count = cursor.fetchone()[0]

        # Get count of incorrect classifications
        cursor.execute(
            """
        SELECT COUNT(*) FROM classification_feedback 
        WHERE ai_category != user_category
        """
        )
        incorrect_count = cursor.fetchone()[0]

        # Get category distribution
        cursor.execute(
            """
        SELECT user_category, COUNT(*) as count 
        FROM classification_feedback 
        GROUP BY user_category
        ORDER BY count DESC
        """
        )
        category_distribution = {row[0]: row[1] for row in cursor.fetchall()}

        # Get most common misclassifications
        cursor.execute(
            """
        SELECT ai_category, user_category, COUNT(*) as count
        FROM classification_feedback
        WHERE ai_category != user_category
        GROUP BY ai_category, user_category
        ORDER BY count DESC
        LIMIT 10
        """
        )
        common_errors = [
            {"ai_category": row[0], "user_category": row[1], "count": row[2]}
            for row in cursor.fetchall()
        ]

        conn.close()

        stats = {
            "total_feedback": total_count,
            "incorrect_classifications": incorrect_count,
            "accuracy": (
                (total_count - incorrect_count) / total_count if total_count > 0 else 0
            ),
            "category_distribution": category_distribution,
            "common_errors": common_errors,
        }

        logger.info(f"Retrieved feedback stats: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Error retrieving feedback stats: {e}")
        return {
            "total_feedback": 0,
            "incorrect_classifications": 0,
            "accuracy": 0,
            "category_distribution": {},
            "common_errors": [],
        }
