# Gmail Classification API Usage Guide

This document provides instructions on how to use the Gmail Classification API with Postman.

## Setup

1. Install the required dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Make sure you have set up your `.env` file with the following variables:

   ```
   EMAIL_ADDRESS=your_gmail@gmail.com
   EMAIL_PASSWORD=your_app_password
   OPENAI_API_KEY=your_openai_api_key
   ```

3. Run the API server:

   ```
   python api.py
   ```

4. The API will be available at `http://localhost:5000`

## API Endpoints

### 1. Get Emails (via IMAP)

**Endpoint:** `GET /api/emails`

**Parameters:**

- `max_emails` (optional): Number of emails to fetch (default: 5)

**Example Request in Postman:**

- URL: `http://localhost:5000/api/emails?max_emails=10`
- Method: GET

**Response:**

```json
{
  "success": true,
  "emails": [
    {
      "subject": "Example Subject",
      "from": "sender@example.com",
      "snippet": "Email content preview...",
      "category": "Work"
    },
    ...
  ]
}
```

### 2. Get Primary Category Emails (via Gmail API)

**Endpoint:** `GET /api/primary-emails`

**Parameters:**

- `max_emails` (optional): Number of emails to fetch (default: 15)

**Example Request in Postman:**

- URL: `http://localhost:5000/api/primary-emails?max_emails=10`
- Method: GET

**Response:**

```json
{
  "success": true,
  "emails": [
    {
      "id": "18c3b4e5d6f7",
      "subject": "Example Subject",
      "from": "sender@example.com",
      "snippet": "Email content preview...",
      "category": "Work"
    },
    ...
  ]
}
```

### 3. Classify Email

**Endpoint:** `POST /api/classify`

**Parameters (JSON body):**

- `subject`: Email subject
- `snippet`: Email content

**Example Request in Postman:**

- URL: `http://localhost:5000/api/classify`
- Method: POST
- Headers:
  - Content-Type: application/json
- Body:

```json
{
  "subject": "Weekly Sports Update",
  "snippet": "Here are this week's top sports highlights..."
}
```

**Response:**

```json
{
  "success": true,
  "category": "Sports"
}
```

### 4. Apply Label to Email

**Endpoint:** `POST /api/label`

**Parameters (JSON body):**

- `message_id`: Gmail message ID
- `category`: Category/label to apply

**Example Request in Postman:**

- URL: `http://localhost:5000/api/label`
- Method: POST
- Headers:
  - Content-Type: application/json
- Body:

```json
{
  "message_id": "18c3b4e5d6f7",
  "category": "Sports"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Applied label 'Sports' to message"
}
```

## Notes

- The API uses OAuth2 for Gmail authentication. The first time you run it, a browser window will open to authorize access.
- The token will be saved as `token.pickle` for future use.
- Make sure your Gmail account has enabled "Less secure app access" or you're using an App Password if you have 2FA enabled.
