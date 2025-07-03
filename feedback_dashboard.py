import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import json
import os
from utils.feedback_db import init_db, get_feedback_stats
from utils.prompt_updater import read_current_prompt, update_prompt_from_feedback

# Initialize the database
init_db()

st.set_page_config(
    page_title="📊 Email Classification Feedback Dashboard", layout="wide"
)
st.title("📊 Email Classification Feedback Dashboard")

# Sidebar for actions
st.sidebar.header("Actions")

if st.sidebar.button("Refresh Data"):
    st.experimental_rerun()

if st.sidebar.button("Trigger Prompt Update"):
    with st.spinner("Updating prompt..."):
        success = update_prompt_from_feedback(
            min_feedback_count=10
        )  # Lower threshold for manual updates
        if success:
            st.sidebar.success("✅ Prompt updated successfully!")
        else:
            st.sidebar.error("❌ Not enough feedback or update failed")

# Get feedback statistics
stats = get_feedback_stats()

# Display overall metrics
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Feedback", stats["total_feedback"])
with col2:
    st.metric("Incorrect Classifications", stats["incorrect_classifications"])
with col3:
    accuracy = stats["accuracy"] * 100 if stats["total_feedback"] > 0 else 0
    st.metric("Accuracy", f"{accuracy:.1f}%")

# Display category distribution
st.header("Category Distribution")
if stats["category_distribution"]:
    categories = list(stats["category_distribution"].keys())
    counts = list(stats["category_distribution"].values())

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(categories, counts)
    ax.set_xlabel("Category")
    ax.set_ylabel("Count")
    ax.set_title("Email Categories Distribution")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    st.pyplot(fig)
else:
    st.info("No category data available yet")

# Display common errors
st.header("Common Misclassifications")
if stats["common_errors"]:
    error_data = []
    for error in stats["common_errors"]:
        error_data.append(
            {
                "AI Prediction": error["ai_category"],
                "Correct Category": error["user_category"],
                "Count": error["count"],
            }
        )

    st.table(pd.DataFrame(error_data))
else:
    st.info("No misclassification data available yet")

# Display current prompt
st.header("Current Classification Prompt")
current_prompt = read_current_prompt()
if current_prompt:
    with st.expander("View Current Prompt"):
        st.code(current_prompt, language="markdown")
else:
    st.warning("Could not read current prompt")

# Add explanation about the feedback system
st.header("About the Feedback System")
st.markdown(
    """
This dashboard shows statistics about email classification feedback. The system:

1. Collects user corrections when AI classifications are wrong
2. Stores these corrections in a SQLite database
3. Periodically analyzes patterns in misclassifications
4. Automatically updates the classification prompt to improve accuracy
5. Keeps a history of prompt versions and performance metrics

The prompt is automatically updated when at least 20 incorrect classifications are collected.
You can also manually trigger an update using the button in the sidebar.
"""
)
