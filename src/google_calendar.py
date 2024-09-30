from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
TIMEZONE = os.getenv('TIMEZONE', 'America/New_York')  # Default to 'America/New_York' if not set

logger = logging.getLogger(__name__)

def get_calendar_service():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        logger.error(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")
        logger.error(f"Current working directory: {os.getcwd()}")
        return None

    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"Error creating calendar service: {str(e)}")
        return None

def add_event_to_calendar(start_time, end_time, summary, description):
    service = get_calendar_service()
    if not service:
        return None

    # Ensure start_time and end_time are in the correct format
    start_datetime = datetime.fromisoformat(start_time)
    end_datetime = datetime.fromisoformat(end_time)

    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_datetime.isoformat(),
            'timeZone': TIMEZONE,
        },
        'end': {
            'dateTime': end_datetime.isoformat(),
            'timeZone': TIMEZONE,
        },
    }

    try:
        event = service.events().insert(calendarId='primary', body=event).execute()
        logger.info(f"Event created: {event.get('htmlLink')}")
        return event.get('id')
    except Exception as error:
        logger.error(f"An error occurred: {error}")
        logger.error(f"Request body: {event}")
        return None