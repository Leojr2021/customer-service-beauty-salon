import os
from dotenv import load_dotenv
import sys
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

load_dotenv()
WORKDIR=os.getenv("WORKDIR")
os.chdir(WORKDIR)
sys.path.append(WORKDIR)

from langchain_core.tools import tool
from src.validators.agent_validators import *
from typing import  Literal
import pandas as pd
import json
from src.vector_database.main import PineconeManagment
from src.utils import format_retrieved_docs
from src.google_calendar import add_event_to_calendar

pinecone_conn = PineconeManagment()
pinecone_conn.loading_vdb(index_name='zenbeautysalon')
retriever = pinecone_conn.vdb.as_retriever(search_type="similarity", search_kwargs={"k": 5})
rag_chain = retriever | format_retrieved_docs

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
        df = pd.read_csv(f"{WORKDIR}/data/syntetic_data/availability.csv")
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
def check_availability_by_service(desired_date: DateModel, service: Literal["hairstylist", "nail_technician", "esthetician", "makeup_artist", "massage_therapist", "eyebrow_specialist", "colorist"]):
    """
    Checking the database if we have availability for the specific service.
    The parameters should be mentioned by the user in the query
    """
    #Dummy data
    df = pd.read_csv(f"{WORKDIR}/data/syntetic_data/availability.csv")
    df['date_slot_time'] = df['date_slot'].apply(lambda input: input.split(' ')[-1])
    rows = df[(df['date_slot'].apply(lambda input: input.split(' ')[0]) == desired_date.date) & 
              (df['service'] == service) & 
              (df['is_available'] == True)]

    if len(rows) == 0:
        return f"No availability for {service} on {desired_date.date}"
    else:
        available_slots = rows['date_slot_time'].tolist()
        output = f'Available slots for {service} on {desired_date.date}:\n'
        output += ", ".join(available_slots)
        return output

@tool
def reschedule_booking(old_date: DateTimeModel, new_date: DateTimeModel, id_number: IdentificationNumberModel, specialist_name: Literal["emma thompson", "olivia parker", "sophia chen", "mia rodriguez", "isabella kim", "ava johnson", "noah williams", "liam davis", "zoe martinez", "ethan brown"]):
    """
    Rescheduling an appointment and updating it in Google Calendar.
    The parameters MUST be mentioned by the user in the query.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Attempting to reschedule appointment: old_date={old_date.date}, new_date={new_date.date}, id={id_number.id}, specialist={specialist_name}")
    
    try:
        df = pd.read_csv(f'{WORKDIR}/data/syntetic_data/availability.csv')
        
        # Check if the new slot is available
        new_slot_available = df[(df['date_slot'] == new_date.date) & 
                                (df['specialist_name'] == specialist_name) & 
                                (df['is_available'] == True)]
        
        if new_slot_available.empty:
            logger.warning("The requested new slot is not available")
            return "The requested new time slot is not available. Please choose a different time."
        
        # Find the old appointment
        old_appointment = df[(df['date_slot'] == old_date.date) & 
                             (df['specialist_name'] == specialist_name) & 
                             (df['client_to_attend'] == float(id_number.id))]
        
        if old_appointment.empty:
            logger.warning("No existing appointment found to reschedule")
            return "No existing appointment found with the provided details. Please check your information and try again."
        
        # Update the old slot to available
        df.loc[old_appointment.index, ['is_available', 'client_to_attend']] = [True, None]
        
        # Book the new slot
        new_slot_index = new_slot_available.index[0]
        df.loc[new_slot_index, ['is_available', 'client_to_attend']] = [False, float(id_number.id)]
        
        # Save the updated DataFrame
        df.to_csv(f'{WORKDIR}/data/syntetic_data/availability.csv', index=False)
        
        # Update event in Google Calendar
        from src.google_calendar import service
        events_result = service.events().list(calendarId='primary', timeMin=old_date.date,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        for event in events:
            if event['summary'] == f"Appointment with {specialist_name}" and event['description'] == f"Client ID: {id_number.id}":
                event['start']['dateTime'] = new_date.date
                event['end']['dateTime'] = (datetime.strptime(new_date.date, "%Y-%m-%d %H:%M") + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
                updated_event = service.events().update(calendarId='primary', eventId=event['id'], body=event).execute()
                break
        
        logger.info("Appointment successfully rescheduled")
        return f"Your appointment has been successfully rescheduled from {old_date.date} to {new_date.date} with {specialist_name}. The Google Calendar event has been updated."
    
    except Exception as e:
        logger.error(f"Error in reschedule_booking: {str(e)}")
        return f"An error occurred while rescheduling the appointment: {str(e)}"

@tool
def cancel_booking(date: DateTimeModel, id_number: IdentificationNumberModel, specialist_name: Literal["emma thompson", "olivia parker", "sophia chen", "mia rodriguez", "isabella kim", "ava johnson", "noah williams", "liam davis", "zoe martinez", "ethan brown"]):
    """
    Canceling an appointment and removing it from Google Calendar.
    The parameters MUST be mentioned by the user in the query.
    """
    df = pd.read_csv(f'{WORKDIR}/data/syntetic_data/availability.csv')
    
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
        return "You don't have any appointment with those specifications"
    else:
        # Update the row
        df.loc[case_to_remove.index, 'is_available'] = True
        df.loc[case_to_remove.index, 'client_to_attend'] = None
        
        # Save the updated DataFrame back to CSV
        df.to_csv(f'{WORKDIR}/data/syntetic_data/availability.csv', index=False)
        
        # Remove event from Google Calendar
        from src.google_calendar import service
        events_result = service.events().list(calendarId='primary', timeMin=date.date,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        for event in events:
            if event['summary'] == f"Appointment with {specialist_name}" and event['description'] == f"Client ID: {id_number.id}":
                service.events().delete(calendarId='primary', eventId=event['id']).execute()
                break
        
        return "Successfully cancelled and removed from Google Calendar"

@tool
def get_salon_services():
    """
    Obtain information about the specialists and services/services we provide.
    The parameters MUST be mentioned by the user in the query
    """
    with open(f"{WORKDIR}/data/catalog.json","r") as file:
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
        df = pd.read_csv(f'{WORKDIR}/data/syntetic_data/availability.csv')
        logger.info(f"Availability data loaded. Shape: {df.shape}")
        
        # Convert desired_date to datetime object
        desired_datetime = datetime.strptime(desired_date.date, "%Y-%m-%d %H:%M")
        
        # Format the date string to match the CSV format
        formatted_date = desired_datetime.strftime("%Y-%m-%d %H:%M")
        
        case = df[(df['date_slot'] == formatted_date) & (df['specialist_name'] == specialist_name) & (df['is_available'] == True)]
        logger.info(f"Matching cases found: {len(case)}")
        
        if len(case) > 0:
            # Update availability
            df.loc[(df['date_slot'] == formatted_date) & (df['specialist_name'] == specialist_name), 'is_available'] = False
            df.loc[(df['date_slot'] == formatted_date) & (df['specialist_name'] == specialist_name), 'client_to_attend'] = id_number.id
            df.to_csv(f'{WORKDIR}/data/syntetic_data/availability.csv', index=False)
            logger.info("Availability updated")
            
            # Add to Google Calendar
            TIMEZONE = os.getenv('TIMEZONE', 'America/New_York')

            start_time = desired_datetime.replace(tzinfo=ZoneInfo(TIMEZONE))
            end_time = start_time + timedelta(hours=1)
            summary = f"Appointment with {specialist_name}"
            description = f"Client ID: {id_number.id}"
            event_id = add_event_to_calendar(start_time.isoformat(), end_time.isoformat(), summary, description)
            
            if event_id:
                logger.info(f"Appointment set and added to Google Calendar. Event ID: {event_id}")
                return f"Appointment set successfully for {start_time.strftime('%Y-%m-%d %H:%M %Z')} with {specialist_name}. Your appointment ID is {event_id}."
            else:
                logger.error("Failed to add event to Google Calendar")
                return "Appointment set in our system, but failed to add to Google Calendar. Please contact support."
        else:
            logger.info("No available slot found")
            return f"Sorry, no available slot found for {specialist_name} on {formatted_date}. Please try a different date or specialist."
    except Exception as e:
        logger.error(f"Error setting appointment: {str(e)}")
        return f"An error occurred while setting the appointment: {str(e)}"

@tool
def check_results(id_number:IdentificationNumberModel):
    """
    Check if the result of the pacient is available.
    The parameters MUST be mentioned by the user in the query
    """
    #Dummy data
    df = pd.read_csv(f'{WORKDIR}/data/syntetic_data/studies_status.csv')
    rows = df[(df['client_id'] == id_number.id)][['medical_study','is_available']]
    if len(rows) == 0:
        return "The client doesn't have any study made"
    else:
        return rows

@tool
def reminder_appointment(id_number:IdentificationNumberModel):
    """
    Returns when the pacient has its appointment with the specialist
    The parameters MUST be mentioned by the user in the query
    """
    df = pd.read_csv(f'{WORKDIR}/data/syntetic_data/availability.csv')
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
    with open(f"{WORKDIR}/data/catalog.json","r") as file:
        catalog = json.loads(file.read())

    return str([{service['service']: [specialist['name'] for specialist in service['specialists']]} for service in catalog])