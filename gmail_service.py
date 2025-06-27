# gmail_service.py

import os.path
import pickle
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("gmail_service")

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def get_gmail_service():
    logger.info("Starting Gmail service authentication process")
    creds = None
    if os.path.exists("token.pickle"):
        logger.info("Found existing token.pickle file")
        with open("token.pickle", "rb") as token:
            logger.info("Loading credentials from token.pickle")
            creds = pickle.load(token)
            logger.info("Credentials loaded successfully")

    if not creds or not creds.valid:
        logger.info("No valid credentials found, initiating OAuth flow")
        try:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            logger.info("Running local server for authentication")
            creds = flow.run_local_server(port=0)
            logger.info("Authentication successful")
            with open("token.pickle", "wb") as token:
                logger.info("Saving new credentials to token.pickle")
                pickle.dump(creds, token)
                logger.info("Credentials saved successfully")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise

    logger.info("Building Gmail API service")
    service = build("gmail", "v1", credentials=creds)
    logger.info("Gmail API service created successfully")
    return service
