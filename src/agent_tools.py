import os
from dotenv import load_dotenv
import sys
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Union
from sqlalchemy import Date, cast

load_dotenv()


from langchain_core.tools import tool
from src.validators.agent_validators import *
from typing import  Literal
import pandas as pd
import json
from src.vector_database.main import PineconeManagment
from src.utils import format_retrieved_docs
from src.google_calendar_service import GoogleCalendarManager
from src.database import get_db, Availability
from sqlalchemy.orm import Session

pinecone_conn = PineconeManagment()
pinecone_conn.loading_vdb(index_name='zenbeautysalon')
retriever = pinecone_conn.vdb.as_retriever(search_type="similarity", search_kwargs={"k": 5})
rag_chain = retriever | format_retrieved_docs

# Initialize GoogleCalendarManager
google_calendar = GoogleCalendarManager()

# Define DateStructure and IdStructure
DateStructure = Union[str, datetime]
IdStructure = Union[str, int]

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
def check_availability_by_specialist(desired_date: dict, specialist_name: str):
    """
    Checking the database if we have availability for the specific specialist.
    The parameters MUST be mentioned by the user in the query
    """
    logger.info(f"Checking availability for date: {desired_date['date']}, specialist: {specialist_name}")
    
    db = next(get_db())
    try:
        date_to_check = datetime.strptime(desired_date['date'], "%Y-%m-%d").date()
        
        # Query the database for available slots
        available_slots = db.query(Availability).filter(
            cast(Availability.date_slot, Date) == date_to_check,
            Availability.specialist_name == specialist_name,
            Availability.is_available == True
        ).all()

        # Extract time slots
        time_slots = [slot.date_slot.strftime("%H:%M") for slot in available_slots]

        if not time_slots:
            logger.info(f"No availability found for {specialist_name} on {date_to_check}")
            return f"No availability for {specialist_name} on {date_to_check}"
        else:
            output = f"Available slots for {specialist_name} on {date_to_check}:\n"
            output += ", ".join(time_slots)
            logger.info(f"Found {len(time_slots)} available slots")
            return output

    except Exception as e:
        logger.error(f"Error checking availability: {str(e)}")
        return f"An error occurred while checking availability: {str(e)}"
    finally:
        db.close()

@tool
def check_availability_by_service(desired_date: str, service: str):
    """
    Check availability for a specific service on a given date.
    
    Args:
    desired_date (str): The date to check availability for, in YYYY-MM-DD format.
    service (str): The name of the service to check availability for.

    Returns:
    str: A formatted string of available time slots for the specified service and date.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Checking availability for service: {service} on date: {desired_date}")
    
    db = next(get_db())
    try:
        # Convert the desired_date string to a datetime object
        date_obj = datetime.strptime(desired_date, "%Y-%m-%d")
        
        # Set the time to the start of the day
        start_of_day = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Set the time to the end of the day
        end_of_day = start_of_day + timedelta(days=1) - timedelta(microseconds=1)
        
        logger.info(f"Query parameters: start={start_of_day}, end={end_of_day}")
        
        # Query the database for available slots
        available_slots = db.query(Availability).filter(
            and_(
                Availability.specialization == service,
                Availability.date_slot >= start_of_day,
                Availability.date_slot <= end_of_day,
                Availability.is_available == True
            )
        ).all()
        
        logger.info(f"Query returned {len(available_slots)} results")
        
        if not available_slots:
            logger.info(f"No availability found for {service} on {date_obj.date()}")
            return f"No availability for {service} on {date_obj.date()}"
        
        # Format the results
        output = f"Available slots for {service} on {date_obj.date()}:\n"
        for slot in available_slots:
            output += f"- {slot.date_slot.strftime('%H:%M')} with {slot.specialist_name}\n"
        
        logger.info(f"Found {len(available_slots)} available slots for {service} on {date_obj.date()}")
        return output
    except Exception as e:
        logger.error(f"Error checking availability: {str(e)}")
        return f"An error occurred while checking availability: {str(e)}"
    finally:
        db.close()

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
def book_appointment(desired_date: str, id_number: str, specialist_name: str):
    """
    Book an appointment with a specialist on a specific date.
    
    Args:
    desired_date (str): The desired date and time for the appointment.
    id_number (str): The identification number of the client.
    specialist_name (str): The name of the specialist for the appointment.

    Returns:
    str: A message confirming the booking or explaining why it couldn't be booked.
    """
    logger.info(f"Attempting to book appointment: {desired_date}, {id_number}, {specialist_name}")
    db = next(get_db())
    try:
        desired_datetime = datetime.strptime(desired_date, "%Y-%m-%d %H:%M")
        
        availability = db.query(Availability).filter(
            Availability.date_slot == desired_datetime,
            Availability.specialist_name == specialist_name,
            Availability.is_available == True
        ).first()
        
        if availability:
            logger.info(f"Availability found for {specialist_name} at {desired_datetime}")
            # Add to Google Calendar
            event = google_calendar.create_event(
                summary=f"Appointment with {specialist_name}",
                start_time=desired_datetime.isoformat(),
                end_time=(desired_datetime + timedelta(hours=1)).isoformat(),
                timezone=os.getenv('TIMEZONE', 'America/New_York')
            )
            
            if event is None:
                logger.error("Failed to add appointment to Google Calendar")
                return "Failed to add appointment to Google Calendar. The appointment is not booked. Please try again or contact support."
            
            logger.info(f"Event added to Google Calendar: {event['id']}")
            
            # Update availability in the database
            availability.is_available = False
            availability.client_to_attend = id_number
            availability.event_id = event['id']
            db.commit()
            logger.info(f"Database updated for appointment: {event['id']}")
            
            return f"Appointment booked successfully for {desired_date} with {specialist_name}. Event ID: {event['id']}"
        else:
            logger.warning(f"No availability found for {specialist_name} at {desired_datetime}")
            return "No availability found for the specified date and specialist."
    except Exception as e:
        logger.error(f"Error booking appointment: {str(e)}")
        return f"An error occurred while booking the appointment: {str(e)}"
    finally:
        db.close()

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

