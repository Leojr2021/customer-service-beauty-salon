import os
from dotenv import load_dotenv
import sys
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

load_dotenv()


from langchain_core.tools import tool
from src.validators.agent_validators import *
from typing import  Literal
import pandas as pd
import json
from src.vector_database.main import PineconeManagment
from src.utils import format_retrieved_docs
from src.google_calendar_service import GoogleCalendarManager

pinecone_conn = PineconeManagment()
pinecone_conn.loading_vdb(index_name='zenbeautysalon')
retriever = pinecone_conn.vdb.as_retriever(search_type="similarity", search_kwargs={"k": 5})
rag_chain = retriever | format_retrieved_docs

# Initialize GoogleCalendarManager
google_calendar = GoogleCalendarManager()

def load_catalog():
    with open('data/catalog.json', 'r') as file:
        return json.load(file)

@tool
def get_specialists_by_service(service_name: str):
    """
    Retrieve specialists for a specific service.
    Use this tool when you need to list specialists for a particular service.
    """
    catalog = load_catalog()
    for service in catalog:
        if service['service'].lower() == service_name.lower():
            return [specialist['name'] for specialist in service['specialists']]
    return []

@tool
def get_service_info(service_name: str):
    """
    Retrieve information about a specific service.
    Use this tool when you need details about a particular service.
    """
    catalog = load_catalog()
    for service in catalog:
        if service['service'].lower() == service_name.lower():
            return service
    return None

#All the tools to consider
@tool
def check_availability_by_specialist(desired_date: DateModel, specialist_name: Literal["emma thompson", "olivia parker", "sophia chen", "mia rodriguez", "isabella kim", "ava johnson", "noah williams", "liam davis", "zoe martinez", "ethan brown"]):
    """
    Checking the database if we have availability for the specific specialist.
    The parameters should be mentioned by the user in the query
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Checking availability for date: {desired_date.date}, specialist: {specialist_name}")

    try:
        # Load the data
        df = pd.read_csv(f"data/syntetic_data/availability.csv")
        logger.info(f"Availability data loaded. Shape: {df.shape}")

        # Filter the dataframe
        available_slots = df[
            (df['date_slot'].str.startswith(desired_date.date)) &
            (df['specialist_name'] == specialist_name) &
            (df['is_available'] == True)
        ]

        # Extract time slots
        time_slots = available_slots['date_slot'].apply(lambda x: x.split(' ')[-1]).tolist()

        if not time_slots:
            logger.info(f"No availability found for {specialist_name} on {desired_date.date}")
            return f"No availability for {specialist_name} on {desired_date.date}"
        else:
            output = f"Available slots for {specialist_name} on {desired_date.date}:\n"
            output += ", ".join(time_slots)
            logger.info(f"Found {len(time_slots)} available slots")
            return output

    except Exception as e:
        logger.error(f"Error checking availability: {str(e)}")
        return f"An error occurred while checking availability: {str(e)}"

@tool
def check_availability_by_service(desired_date: DateModel, service: str):
    """
    Check availability for a specific service on a given date.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Checking availability for service: {service} on date: {desired_date.date}")

    try:
        df = pd.read_csv(f"data/syntetic_data/availability.csv")
        
        # Filter the dataframe for the specific date and service
        available_slots = df[
            (df['date_slot'].str.startswith(desired_date.date)) &
            (df['service'] == service) &
            (df['is_available'] == True)
        ]

        if available_slots.empty:
            return f"No availability for {service} on {desired_date.date}"
        
        time_slots = available_slots['date_slot'].apply(lambda x: x.split(' ')[-1]).tolist()
        return f"Available slots for {service} on {desired_date.date}: {', '.join(time_slots)}"

    except Exception as e:
        logger.error(f"Error checking availability: {str(e)}")
        return f"An error occurred while checking availability: {str(e)}"

@tool
def reschedule_booking(old_date: DateTimeModel, new_date: DateTimeModel, id_number: IdentificationNumberModel, specialist_name: Literal["emma thompson", "olivia parker", "sophia chen", "mia rodriguez", "isabella kim", "ava johnson", "noah williams", "liam davis", "zoe martinez", "ethan brown"]):
    """
    Rescheduling an appointment and updating it in Google Calendar.
    The parameters MUST be mentioned by the user in the query.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Attempting to reschedule appointment: old_date={old_date.date}, new_date={new_date.date}, id={id_number.id}, specialist={specialist_name}")
    
    try:
        df = pd.read_csv(f'data/syntetic_data/availability.csv')
        
        # Find the old appointment first
        old_appointment = df[(df['date_slot'] == old_date.date) & 
                             (df['specialist_name'] == specialist_name) & 
                             (df['client_to_attend'] == float(id_number.id))]
        
        if old_appointment.empty:
            logger.warning("No existing appointment found to reschedule")
            return "No existing appointment found with the provided details. Please check your information and try again."
        
        # Check if the new slot is available
        new_slot_available = df[(df['date_slot'] == new_date.date) & 
                                (df['specialist_name'] == specialist_name) & 
                                (df['is_available'] == True)]
        
        if new_slot_available.empty:
            logger.warning("The requested new slot is not available")
            return "The requested new time slot is not available. Please choose a different time."
        
        # Get the event_id from the old appointment
        event_id = old_appointment['event_id'].iloc[0]
        
        # Update the Google Calendar event
        TIMEZONE = os.getenv('TIMEZONE', 'America/New_York')
        new_datetime = datetime.strptime(new_date.date, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(TIMEZONE))
        
        updated_event = google_calendar.update_event(
            event_id,
            summary=f"Appointment with {specialist_name}",
            start_time=new_datetime.isoformat(),
            end_time=(new_datetime + timedelta(hours=1)).isoformat(),
            timezone=TIMEZONE
        )

        if updated_event:
            # Update the availability data
            df.loc[old_appointment.index, 'is_available'] = True
            df.loc[old_appointment.index, 'client_to_attend'] = None
            df.loc[old_appointment.index, 'event_id'] = None
            
            df.loc[new_slot_available.index, 'is_available'] = False
            df.loc[new_slot_available.index, 'client_to_attend'] = id_number.id
            df.loc[new_slot_available.index, 'event_id'] = event_id
            
            df.to_csv(f'data/syntetic_data/availability.csv', index=False)
            logger.info("Availability updated after rescheduling")

            return f"Appointment rescheduled successfully to {new_datetime.strftime('%Y-%m-%d %H:%M %Z')} with {specialist_name}."
        else:
            return "Failed to reschedule the appointment. Please try again or contact support."

    except Exception as e:
        logger.error(f"Error in reschedule_booking: {str(e)}")
        return f"An error occurred while rescheduling the appointment: {str(e)}"

@tool
def cancel_booking(date: DateTimeModel, id_number: IdentificationNumberModel, specialist_name: Literal["emma thompson", "olivia parker", "sophia chen", "mia rodriguez", "isabella kim", "ava johnson", "noah williams", "liam davis", "zoe martinez", "ethan brown"]):
    """
    Canceling an appointment and removing it from Google Calendar.
    The parameters MUST be mentioned by the user in the query.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Attempting to cancel appointment: date={date.date}, id={id_number.id}, specialist={specialist_name}")
    
    try:
        df = pd.read_csv(f'data/syntetic_data/availability.csv')
        
        # Convert client_to_attend to float for comparison
        df['client_to_attend'] = pd.to_numeric(df['client_to_attend'], errors='coerce')
        
        # Convert date to string for comparison
        date_str = date.date.split()[0]  # Extract just the date part
        
        case_to_remove = df[
            (df['date_slot'].str.startswith(date_str)) &
            (df['client_to_attend'] == float(id_number.id)) &
            (df['specialist_name'] == specialist_name)
        ]
        
        if case_to_remove.empty:
            logger.warning("No appointment found to cancel")
            return "You don't have any appointment with those specifications"
        else:
            # Get the event_id before updating the row
            event_id = case_to_remove['event_id'].iloc[0]
            
            # Update the row
            df.loc[case_to_remove.index, 'is_available'] = True
            df.loc[case_to_remove.index, 'client_to_attend'] = None
            df.loc[case_to_remove.index, 'event_id'] = None
            
            # Save the updated DataFrame back to CSV
            df.to_csv(f'data/syntetic_data/availability.csv', index=False)
            logger.info("Availability updated after cancellation")
            
            # Remove event from Google Calendar
            if event_id:
                google_calendar.delete_event(event_id)
                logger.info(f"Event {event_id} deleted from Google Calendar")
                return "Successfully cancelled and removed from Google Calendar"
            else:
                logger.warning("No event_id found for the appointment")
                return "Appointment cancelled in our system, but no corresponding Google Calendar event found. Please contact support if you have any concerns."
    
    except Exception as e:
        logger.error(f"Error in cancel_booking: {str(e)}")
        return f"An error occurred while cancelling the appointment: {str(e)}"

@tool
def get_salon_services():
    """
    Obtain information about the specialists and services/services we provide.
    The parameters MUST be mentioned by the user in the query
    """
    with open(f"data/catalog.json","r") as file:
        file = json.loads(file.read())
    
    return file

@tool
def book_appointment(desired_date: DateTimeModel, id_number: IdentificationNumberModel, specialist_name: Literal["emma thompson", "olivia parker", "sophia chen", "mia rodriguez", "isabella kim", "ava johnson", "noah williams", "liam davis", "zoe martinez", "ethan brown"]):
    """
    Set appointment with the specialist and add it to Google Calendar.
    The parameters MUST be mentioned by the user in the query.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Attempting to set appointment with parameters: date={desired_date.date}, id={id_number.id}, specialist={specialist_name}")
    try:
        df = pd.read_csv(f'data/syntetic_data/availability.csv')
        logger.info(f"Availability data loaded. Shape: {df.shape}")
        
        # Convert desired_date to datetime object
        desired_datetime = datetime.strptime(desired_date.date, "%Y-%m-%d %H:%M")
        
        # Format the date string to match the CSV format
        formatted_date = desired_datetime.strftime("%Y-%m-%d %H:%M")
        
        case = df[(df['date_slot'] == formatted_date) & (df['specialist_name'] == specialist_name) & (df['is_available'] == True)]
        logger.info(f"Matching cases found: {len(case)}")
        
        if len(case) > 0:
            # Add to Google Calendar
            TIMEZONE = os.getenv('TIMEZONE', 'America/New_York')

            start_time = desired_datetime.astimezone(ZoneInfo(TIMEZONE))
            end_time = start_time + timedelta(hours=1)
            summary = f"Appointment with {specialist_name}"
            description = f"Client ID: {id_number.id}"
            
            logger.info(f"Attempting to create Google Calendar event: summary={summary}, start_time={start_time.isoformat()}, end_time={end_time.isoformat()}, timezone={TIMEZONE}")
            
            event = google_calendar.create_event(summary, start_time.isoformat(), end_time.isoformat(), TIMEZONE)
            
            if event is None:
                logger.error("Failed to create event in Google Calendar")
                return "Failed to add appointment to Google Calendar. The appointment is not booked. Please try again or contact support."
            
            event_id = event['id']
            logger.info(f"Appointment added to Google Calendar with event ID: {event_id}")
            
            # Update availability
            df.loc[(df['date_slot'] == formatted_date) & (df['specialist_name'] == specialist_name), 'is_available'] = False
            df.loc[(df['date_slot'] == formatted_date) & (df['specialist_name'] == specialist_name), 'client_to_attend'] = id_number.id
            df.loc[(df['date_slot'] == formatted_date) & (df['specialist_name'] == specialist_name), 'event_id'] = event_id
            df.to_csv(f'data/syntetic_data/availability.csv', index=False)
            logger.info("Availability updated with event ID")
            
            return f"Appointment set successfully for {start_time.strftime('%Y-%m-%d %H:%M %Z')} with {specialist_name}."
        else:
            logger.info("No available slot found")
            return f"Sorry, no available slot found for {specialist_name} on {formatted_date}. Please try a different date or specialist."
    except Exception as e:
        logger.error(f"Error setting appointment: {str(e)}")
        return f"An error occurred while setting the appointment: {str(e)}"


@tool
def reminder_appointment(id_number:IdentificationNumberModel):
    """
    Returns when the pacient has its appointment with the specialist
    The parameters MUST be mentioned by the user in the query
    """
    df = pd.read_csv(f'data/syntetic_data/availability.csv')
    rows = df[(df['client_to_attend'] == id_number.id)][['time_slot','specialist_name','service']]
    if len(rows) == 0:
        return "The client doesn't have any appointment yet"
    else:
        return rows


@tool
def retrieve_faq_info(question:str):
    """
    Retrieve documents or additional info from general questions about the beauty salon.
    Call this tool if question is regarding center:
    For example: is it open? Do you have parking? Can  I go with bike? etc...
    """
    results = rag_chain.invoke(question)
    if results.startswith("I couldn't find an exact match"):
        return results + " If you need more specific information, please feel free to ask, and I'll do my best to help or direct you to the right resource."
    return results

@tool
def get_specialist_services(specialist_name:Literal["emma thompson","olivia parker","sophia chen","mia rodriguez","isabella kim","ava johnson","noah williams","liam davis","zoe martinez","ethan brown"]):
    """
    Retrieve which service covers a specific specialist.
    Use this internal tool if you need more information about a specialist for setting an appointment.
    """
    with open(f"data/catalog.json","r") as file:
        catalog = json.loads(file.read())

    return str([{service['service']: [specialist['name'] for specialist in service['specialists']]} for service in catalog])