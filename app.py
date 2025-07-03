import streamlit as st
import pandas as pd
from email_classifier import fetch_emails, classify_email
from utils.excel_conversion import convert_csv_to_excel
from utils.feedback_db import init_db, store_feedback

# Initialize the feedback database
init_db()

st.set_page_config(page_title="📧 AI Email Classifier", layout="wide")
st.title("📧 AI Email Classifier with Manual Override")

# Load emails
emails = fetch_emails(5)
feedback_data = []

# UI for each email
for i, mail in enumerate(emails):
    subject = mail["subject"]
    sender = mail["from"]
    snippet = mail["snippet"]
    message_id = mail.get("id", f"local_{i}")  # Use message ID if available
    ai_label = classify_email(subject, snippet)

    category_options = [
        "Sports",
        "Entertainment",
        "Job Applications",
        "Conferences",
        "Promotions",
        "Work",
        "Other",
    ]

    with st.expander(f"Email #{i+1}: {subject}"):
        st.markdown(f"**From**: {sender}")
        st.markdown("**Snippet:**")
        st.code(snippet, language="text")
        st.markdown(f"**AI Prediction**:  `{ai_label}`")

        user_label = st.radio(
            f"📝 Your category for Email #{i+1}:",
            options=category_options,
            index=(
                category_options.index(ai_label)
                if ai_label in category_options
                else category_options.index("Other")
            ),
            key=f"user_label_{i}",
        )

        # Store feedback if user changed the classification
        if user_label != ai_label:
            st.info(
                f"You changed the classification from '{ai_label}' to '{user_label}'"
            )

            # Store feedback in database
            store_feedback(
                message_id=message_id,
                subject=subject,
                snippet=snippet,
                ai_category=ai_label,
                user_category=user_label,
            )

        feedback_data.append(
            {
                "Subject": subject,
                "From": sender,
                "Snippet": snippet,
                "AI_Category": ai_label,
                "User_Category": user_label,
            }
        )

# Save feedback
if st.button("Save Feedback to CSV"):
    df = pd.DataFrame(feedback_data)
    df.to_csv("email_classification_log.csv", index=False)
    convert_csv_to_excel("email_classification_log.csv")
    st.success("✅ Feedback saved to `email_classification_log.csv`")

    with open("cleaned_email_data.xlsx", "rb") as f:
        st.download_button(
            label="Download Cleaned Excel",
            data=f,
            file_name="email_classification_log_cleaned.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# Link to feedback dashboard
st.sidebar.markdown("---")
st.sidebar.header("📊 Analytics")
if st.sidebar.button("Open Feedback Dashboard"):
    st.sidebar.info("Running feedback_dashboard.py...")
    import subprocess

    subprocess.Popen(["streamlit", "run", "feedback_dashboard.py"])
