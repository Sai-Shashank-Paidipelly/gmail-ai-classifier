# Email Classification Feedback System

This document explains the feedback system implemented for the Gmail AI Classifier. The system collects user corrections when AI classifications are wrong, stores them in a database, and periodically uses this feedback to improve the classification prompt.

## Overview

The feedback system consists of the following components:

1. **Feedback Collection**: When users correct AI classifications, their corrections are stored in a SQLite database.
2. **Feedback Analysis**: Statistics about classification accuracy are calculated and displayed in a dashboard.
3. **Prompt Improvement**: Periodically, the system analyzes patterns in misclassifications and updates the classification prompt.
4. **Version History**: All prompt versions are backed up and tracked with performance metrics.

## Database Schema

The feedback system uses SQLite with two main tables:

### `classification_feedback`

Stores individual feedback entries:

- `id`: Unique identifier for the feedback entry
- `message_id`: Gmail message ID
- `subject`: Email subject
- `snippet`: Email snippet/content
- `ai_category`: Category predicted by AI
- `user_category`: Category corrected by user
- `timestamp`: When the feedback was recorded
- `is_processed`: Whether this feedback has been used to update the prompt

### `prompt_updates`

Tracks history of prompt updates:

- `id`: Unique identifier for the update
- `old_prompt`: Previous prompt text
- `new_prompt`: Updated prompt text
- `timestamp`: When the update occurred
- `feedback_count`: Number of feedback entries used for this update
- `performance_metrics`: JSON string with metrics about the update

## How It Works

### 1. Collecting Feedback

Feedback is collected in two ways:

- **Web UI**: When users correct classifications in the Streamlit app
- **API**: Through the `/api/feedback` endpoint

Example API request:

```json
POST /api/feedback
{
  "message_id": "18c3b4e5d6f7",
  "ai_category": "Promotions",
  "user_category": "Work",
  "subject": "Project Update",
  "snippet": "Here's the latest update on our project..."
}
```

### 2. Analyzing Feedback

The system tracks:

- Total number of classifications
- Number of incorrect classifications
- Classification accuracy percentage
- Distribution of categories
- Most common misclassification patterns

These statistics are available through:

- The feedback dashboard (`feedback_dashboard.py`)
- The `/api/feedback/stats` API endpoint

### 3. Improving the Prompt

Prompt improvement happens:

- **Automatically**: When at least 20 incorrect classifications are collected, the scheduled task (`scheduled_updates.py`) will trigger an update.
- **Manually**: Users can trigger an update through the dashboard or the `/api/prompt/update` API endpoint.

The improvement process:

1. Collect unprocessed feedback entries
2. Analyze patterns in misclassifications
3. Use OpenAI to generate an improved prompt
4. Back up the old prompt
5. Save the new prompt
6. Mark feedback as processed
7. Record the update in the history

### 4. Tracking Performance

Each time the prompt is updated, the system:

1. Creates a backup of the old prompt with timestamp
2. Records metrics about the update
3. Tracks which feedback entries were used

## Using the System

### Running the Feedback Dashboard

```bash
streamlit run feedback_dashboard.py
```

### Running the Scheduled Updates

```bash
python scheduled_updates.py
```

### Manually Triggering a Prompt Update

```bash
curl -X POST http://localhost:5001/api/prompt/update -H "Content-Type: application/json" -d '{"min_feedback": 10}'
```

## Configuration

The feedback system can be configured by modifying:

- Minimum feedback threshold for updates (`min_feedback_count` in `update_prompt_from_feedback()`)
- Schedule for automatic updates (in `scheduled_updates.py`)
- Database location (`DB_PATH` in `feedback_db.py`)

## Extending the System

To extend the feedback system:

1. **Add new metrics**: Modify `get_feedback_stats()` in `feedback_db.py`
2. **Change prompt update logic**: Modify `generate_improved_prompt()` in `prompt_updater.py`
3. **Add more visualization**: Enhance `feedback_dashboard.py` with additional charts

## Troubleshooting

- **Database issues**: Check `feedback.db` permissions and integrity
- **Prompt update failures**: Check the logs in `scheduled_updates.log`
- **API errors**: Check the Flask server logs
