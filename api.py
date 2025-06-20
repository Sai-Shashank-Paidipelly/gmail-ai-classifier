from flask import Flask, jsonify, request
import os
from email_classifier import fetch_emails, classify_email
from gmail_service import get_gmail_service
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route("/api/emails", methods=["GET"])
def get_emails():
    try:
        # Get max_emails parameter from query string, default to 5
        max_emails = request.args.get("max_emails", default=5, type=int)
        emails = fetch_emails(max_emails)

        # Add classification to each email
        for email in emails:
            email["category"] = classify_email(email["subject"], email["snippet"])

        return jsonify({"success": True, "emails": emails})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/primary-emails", methods=["GET"])
def get_primary_emails():
    try:
        # Get max_emails parameter from query string, default to 15
        max_emails = request.args.get("max_emails", default=15, type=int)

        service = get_gmail_service()
        messages = (
            service.users()
            .messages()
            .list(userId="me", q="category:primary", maxResults=max_emails)
            .execute()
            .get("messages", [])
        )

        emails_data = []

        for message in messages:
            msg_id = message["id"]
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )
            headers = msg["payload"]["headers"]

            subject = next(
                (h["value"] for h in headers if h["name"].lower() == "subject"),
                "(No Subject)",
            )
            sender = next(
                (h["value"] for h in headers if h["name"].lower() == "from"),
                "(No Sender)",
            )

            snippet = msg.get("snippet", "")
            ai_category = classify_email(subject, snippet)

            emails_data.append(
                {
                    "id": msg_id,
                    "subject": subject,
                    "from": sender,
                    "snippet": snippet,
                    "category": ai_category,
                }
            )

        return jsonify({"success": True, "emails": emails_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/classify", methods=["POST"])
def classify():
    try:
        data = request.json
        if not data or "subject" not in data or "snippet" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Missing required fields: subject and snippet",
                    }
                ),
                400,
            )

        category = classify_email(data["subject"], data["snippet"])
        return jsonify({"success": True, "category": category})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/label", methods=["POST"])
def label_email():
    try:
        data = request.json
        if not data or "message_id" not in data or "category" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Missing required fields: message_id and category",
                    }
                ),
                400,
            )

        service = get_gmail_service()

        # Get or create label
        labels = service.users().labels().list(userId="me").execute().get("labels", [])
        label_id = None

        for label in labels:
            if label["name"].lower() == data["category"].lower():
                label_id = label["id"]
                break

        if not label_id:
            label_obj = {
                "name": data["category"],
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            new_label = (
                service.users().labels().create(userId="me", body=label_obj).execute()
            )
            label_id = new_label["id"]

        # Apply label
        service.users().messages().modify(
            userId="me", id=data["message_id"], body={"addLabelIds": [label_id]}
        ).execute()

        return jsonify(
            {
                "success": True,
                "message": f"Applied label '{data['category']}' to message",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
