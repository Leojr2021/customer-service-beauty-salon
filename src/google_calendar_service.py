import os
from dotenv import load_dotenv
import datetime as dt
import json
from google.oauth2.service_account import Credentials  # Correct import
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()  

SCOPES = ["https://www.googleapis.com/auth/calendar"]

GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON', '{}')


class GoogleCalendarManager:
    def __init__(self):
        self.service = self._authenticate()
        self.calendar_id = 'leo.mancilla.dev@gmail.com'  

    def _authenticate(self):
        service_account_json = GOOGLE_SERVICE_ACCOUNT_JSON
        
        if not service_account_json:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON environment variable is not set")

        try:
            info = json.loads(service_account_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)  # This should work now
            return build("calendar", "v3", credentials=creds)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON environment variable")
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            raise


    def list_upcoming_events(self, max_results=10):
        now = dt.datetime.utcnow().isoformat() + "Z"
        tomorrow = (dt.datetime.now() + dt.timedelta(days=5)).replace(hour=23, minute=59, second=0, microsecond=0).isoformat() + "Z"

        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id, timeMin=now, timeMax=tomorrow,
                maxResults=max_results, singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            if not events:
                print('No upcoming events found.')
            else:
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    print(start, event['summary'], event['id'])
            
            return events
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []

    def create_event(self, summary, start_time, end_time, timezone):
        try:
            event = {
                'summary': summary,
                'start': {'dateTime': start_time, 'timeZone': timezone},
                'end': {'dateTime': end_time, 'timeZone': timezone},
            }
            created_event = self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
            return created_event
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None

    def update_event(self, event_id, summary, start_time, end_time, timezone):
        event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
        
        event['summary'] = summary
        event['start'] = {'dateTime': start_time, 'timeZone': timezone}
        event['end'] = {'dateTime': end_time, 'timeZone': timezone}

        updated_event = self.service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        return updated_event

    def delete_event(self, event_id):
        self.service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()
        return True

    def search_events(self, start_time, end_time, q=None):
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=start_time,
            timeMax=end_time,
            q=q,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])


if __name__ == "__main__":
    
    try:
        calendar = GoogleCalendarManager()
        print("Successfully created GoogleCalendarManager instance")
        
        # Test the connection by listing upcoming events
        events = calendar.list_upcoming_events()
        print(f"Successfully retrieved {len(events)} upcoming events")
        
        # Test creating an event
        calendar.create_event(
            "Test Event",
            "2024-10-07T09:10:00-07:00",
            "2024-10-07T10:10:00-07:00",
            "America/Los_Angeles"
            
        )
        
        # Test updating an event
        # updated_event = calendar.update_event(
        #     "g6qoh58u8mvt5vv5mkqbrtp8a8",
        #     summary="Updated Event",
        #     start_time="2024-10-09T09:10:00-07:00",
        #     end_time="2024-10-09T10:10:00-07:00"
        # )
        # print(f"Event updated: {updated_event.get('htmlLink')}")
        
        # Test deleting an event
        # calendar.delete_event("g6qoh58u8mvt5vv5mkqbrtp8a8")
        # print("Event deleted")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
