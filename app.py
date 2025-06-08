import streamlit as st
import pandas as pd
from email_classifier import fetch_emails, classify_email

st.set_page_config(page_title="📧 AI Email Classifier", layout="wide")
st.title("📧 AI Email Classifier with Manual Override")

# Load emails
emails = fetch_emails(5)
feedback_data = []

# UI for each email
for i, mail in enumerate(emails):
    subject = mail['subject']
    sender = mail['from']
    snippet = mail['snippet']
    ai_label = classify_email(subject, snippet)

    with st.expander(f"📨 Email #{i+1}: {subject}"):
        st.markdown(f"**From**: {sender}")
        st.markdown("**Snippet:**")
        st.code(snippet, language="text")
        st.markdown(f"**AI Prediction**: `{ai_label}`")

        user_label = st.radio(
            f"📝 Your label for Email #{i+1}:",
            options=["Important", "Promotional"],
            index=0 if ai_label == "Important" else 1,
            key=f"user_label_{i}"
        )

        feedback_data.append({
            "Subject": subject,
            "From": sender,
            "Snippet": snippet,
            "AI_Label": ai_label,
            "User_Label": user_label
        })

# Save feedback
if st.button("💾 Save Feedback to CSV"):
    df = pd.DataFrame(feedback_data)
    df.to_csv("email_classification_log.csv", index=False)
    st.success("Feedback saved to email_classification_log.csv ✅")
