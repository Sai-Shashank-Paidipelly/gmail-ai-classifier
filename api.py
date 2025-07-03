from flask import Flask, jsonify, request
import os
from email_classifier import classify_email
from gmail_service import get_gmail_service
from flask_cors import CORS
from label_emails import fetch_primary_emails, get_or_create_label
from email_classifier import get_categories_from_prompt
from dotenv import load_dotenv
import traceback
from utils.feedback_db import init_db, store_feedback, get_feedback_stats
from utils.prompt_updater import update_prompt_from_feedback

# Load environment variables
load_dotenv()

# Initialize the feedback database
init_db()

app = Flask(__name__)
CORS(app)


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


@app.route("/api/emails/primary", methods=["GET"])
def get_primary_emails_api():
    """API endpoint to fetch primary emails that haven't been categorized yet"""
    try:
        # Get query parameters with defaults
        max_results = request.args.get("max_results", default=10, type=int)

        # Get Gmail service with error handling
        try:
            service = get_gmail_service()
            print("Successfully authenticated with Gmail API")
        except Exception as auth_error:
            print(f"Authentication error: {str(auth_error)}")
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Gmail API authentication failed: {str(auth_error)}",
                        "error_type": "authentication",
                    }
                ),
                403,
            )

        # Get categories and their label IDs
        try:
            categories = get_categories_from_prompt()
            print(f"Found categories: {categories}")

            # Get all labels
            labels_response = service.users().labels().list(userId="me").execute()
            all_labels = labels_response.get("labels", [])
            print(f"Found {len(all_labels)} labels in Gmail")

            # Find label IDs that match our categories
            category_label_ids = []
            for category in categories:
                for label in all_labels:
                    if category.lower() == label["name"].lower():
                        category_label_ids.append(label["id"])
                        print(
                            f"Matched category '{category}' to label ID: {label['id']}"
                        )
        except Exception as category_error:
            print(f"Error getting categories or labels: {str(category_error)}")
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Failed to get categories or labels: {str(category_error)}",
                        "error_type": "categories_labels",
                    }
                ),
                500,
            )

        # Fetch emails that don't have our classification labels
        try:
            messages = fetch_primary_emails(
                service,
                max_results=max_results,
                label_ids_to_exclude=category_label_ids,
            )
            print(f"Fetched {len(messages)} primary emails")
        except Exception as fetch_error:
            print(f"Error fetching emails: {str(fetch_error)}")
            print(traceback.format_exc())
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Failed to fetch emails: {str(fetch_error)}",
                        "error_type": "fetch_emails",
                    }
                ),
                500,
            )

        # Process messages to return
        email_data = []
        for msg in messages:
            try:
                msg_id = msg["id"]

                # Get full message details
                msg_data = (
                    service.users().messages().get(userId="me", id=msg_id).execute()
                )

                # Extract email details
                headers = msg_data.get("payload", {}).get("headers", [])
                subject = next(
                    (h["value"] for h in headers if h["name"].lower() == "subject"),
                    "(No Subject)",
                )
                sender = next(
                    (h["value"] for h in headers if h["name"].lower() == "from"),
                    "(No Sender)",
                )
                date = next(
                    (h["value"] for h in headers if h["name"].lower() == "date"), ""
                )
                snippet = msg_data.get("snippet", "")

                email_data.append(
                    {
                        "id": msg_id,
                        "subject": subject,
                        "from": sender,
                        "date": date,
                        "snippet": snippet,
                    }
                )
            except Exception as process_error:
                print(
                    f"Error processing message {msg.get('id', 'unknown')}: {str(process_error)}"
                )
                # Continue processing other messages

        return jsonify(
            {"status": "success", "count": len(email_data), "emails": email_data}
        )

    except Exception as e:
        print(f"Unexpected error in API: {str(e)}")
        print(traceback.format_exc())
        return (
            jsonify({"status": "error", "message": str(e), "error_type": "general"}),
            500,
        )


@app.route("/api/emails/classify", methods=["POST"])
def classify_email_api():
    """API endpoint to classify an email and apply a label"""
    try:
        data = request.json
        if not data or "email_id" not in data:
            return (
                jsonify({"status": "error", "message": "Missing email_id in request"}),
                400,
            )

        email_id = data["email_id"]

        # Get Gmail service
        service = get_gmail_service()

        # Get email details
        msg_data = service.users().messages().get(userId="me", id=email_id).execute()

        # Extract subject and snippet
        headers = msg_data.get("payload", {}).get("headers", [])
        subject = next(
            (h["value"] for h in headers if h["name"].lower() == "subject"),
            "(No Subject)",
        )
        snippet = msg_data.get("snippet", "")

        # Classify the email
        category = classify_email(subject, snippet)

        # Apply the label
        label_id = get_or_create_label(service, category)
        service.users().messages().modify(
            userId="me", id=email_id, body={"addLabelIds": [label_id]}
        ).execute()

        return jsonify(
            {"status": "success", "email_id": email_id, "category": category}
        )

    except Exception as e:
        print(f"Error in API: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/feedback", methods=["POST"])
def submit_feedback():
    """Endpoint to submit feedback about email classification"""
    try:
        data = request.json
        if (
            not data
            or "message_id" not in data
            or "ai_category" not in data
            or "user_category" not in data
        ):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Missing required fields: message_id, ai_category, user_category",
                    }
                ),
                400,
            )

        # Get email details if not provided
        subject = data.get("subject", "")
        snippet = data.get("snippet", "")

        if not subject or not snippet:
            try:
                service = get_gmail_service()
                msg_data = (
                    service.users()
                    .messages()
                    .get(userId="me", id=data["message_id"])
                    .execute()
                )

                headers = msg_data.get("payload", {}).get("headers", [])
                subject = next(
                    (h["value"] for h in headers if h["name"].lower() == "subject"),
                    "(No Subject)",
                )
                snippet = msg_data.get("snippet", "")
            except Exception as e:
                print(f"Error fetching email details: {e}")
                # Continue with empty subject/snippet if we can't fetch them

        # Store the feedback
        success = store_feedback(
            message_id=data["message_id"],
            subject=subject,
            snippet=snippet,
            ai_category=data["ai_category"],
            user_category=data["user_category"],
        )

        if not success:
            return jsonify({"success": False, "error": "Failed to store feedback"}), 500

        # If AI was wrong and user corrected it, apply the correct label
        if data["ai_category"] != data["user_category"]:
            try:
                service = get_gmail_service()
                label_id = get_or_create_label(service, data["user_category"])

                # Remove AI's label if it exists
                ai_label_id = None
                labels = (
                    service.users()
                    .labels()
                    .list(userId="me")
                    .execute()
                    .get("labels", [])
                )
                for label in labels:
                    if label["name"].lower() == data["ai_category"].lower():
                        ai_label_id = label["id"]
                        break

                modify_request = {}
                if label_id:
                    modify_request["addLabelIds"] = [label_id]
                if ai_label_id:
                    modify_request["removeLabelIds"] = [ai_label_id]

                if modify_request:
                    service.users().messages().modify(
                        userId="me", id=data["message_id"], body=modify_request
                    ).execute()
            except Exception as e:
                print(f"Error updating labels: {e}")
                # Continue even if label update fails

        return jsonify({"success": True, "message": "Feedback recorded successfully"})
    except Exception as e:
        print(f"Error in feedback submission: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/feedback/stats", methods=["GET"])
def get_stats():
    """Get statistics about classification feedback"""
    try:
        stats = get_feedback_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/prompt/update", methods=["POST"])
def trigger_prompt_update():
    """Manually trigger a prompt update based on feedback"""
    try:
        data = request.json
        min_feedback = data.get("min_feedback", 20) if data else 20

        success = update_prompt_from_feedback(min_feedback_count=min_feedback)

        if success:
            return jsonify({"success": True, "message": "Prompt updated successfully"})
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Not enough feedback or update failed",
                    }
                ),
                400,
            )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
