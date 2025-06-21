# Gmail AI Classifier

A Python-based REST API and utility for automatically classifying Gmail emails into categories using AI (such as OpenAI models), and applying Gmail labels accordingly. The system enables you to fetch, classify, and categorize emails in your Gmail inbox, making it easier to manage and organize your emails.

## Features

- **Fetch Emails:** Retrieve emails from your Gmail inbox using IMAP or Gmail API.
- **AI-Powered Categorization:** Automatically classify emails into categories such as "Sports", "Entertainment", "Job Applications", "Conferences", "Promotions", "Work", and "Other".
- **Apply Gmail Labels:** Assign Gmail labels to emails based on their classified category.
- **RESTful API:** Expose endpoints for programmatic access to email retrieval, classification, and labeling.
- **OAuth2 Authentication:** Securely access your Gmail account with OAuth2.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   Create a `.env` file in the root directory with the following variables:
   ```
   EMAIL_ADDRESS=your_gmail@gmail.com
   EMAIL_PASSWORD=your_app_password
   OPENAI_API_KEY=your_openai_api_key
   ```

3. **Authenticate with Gmail:**
   - On first run, a browser window will open to authorize Gmail access with OAuth2.
   - The token will be saved as `token.pickle` for future use.
   - Ensure "Less secure app access" is enabled, or use an App Password if you have 2FA.

4. **Run the API server:**
   ```bash
   python api.py
   ```
   The API will be available at [http://localhost:5000](http://localhost:5000)

## API Endpoints

### 1. Get Emails (IMAP)
- **Endpoint:** `GET /api/emails`
- **Parameters:** `max_emails` (optional, default: 5)
- **Response:**
  ```json
  {
    "success": true,
    "emails": [
      {
        "subject": "Example Subject",
        "from": "sender@example.com",
        "snippet": "Email content preview...",
        "category": "Work"
      }
    ]
  }
  ```

### 2. Get Primary Category Emails (Gmail API)
- **Endpoint:** `GET /api/primary-emails`
- **Parameters:** `max_emails` (optional, default: 15)
- **Response:** Similar to above, includes email `id`.

### 3. Classify Email
- **Endpoint:** `POST /api/classify`
- **Request body:**
  ```json
  {
    "subject": "Weekly Sports Update",
    "snippet": "Here are this week's top sports highlights..."
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "category": "Sports"
  }
  ```

### 4. Apply Label to Email
- **Endpoint:** `POST /api/label`
- **Request body:**
  ```json
  {
    "message_id": "18c3b4e5d6f7",
    "category": "Sports"
  }
  ```
- **Response:**
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

## Requirements

- Python 3.7+
- See `requirements.txt` for package dependencies.

## License

MIT License

---

**Author:** Sai Shashank Paidipelly
