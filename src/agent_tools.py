import os
from dotenv import load_dotenv
import sys
import logging

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
from langchain_openai import OpenAIEmbeddings

pinecone_conn = PineconeManagment()
pinecone_conn.loading_vdb(index_name='zenbeautysalon')
retriever = pinecone_conn.vdb.as_retriever(search_type="similarity", search_kwargs={"k": 5})
rag_chain = retriever | format_retrieved_docs

#All the tools to consider
@tool
def check_availability_by_specialist (desired_date:DateModel, specialist_name:Literal["emma thompson","olivia parker","sophia chen","mia rodriguez","isabella kim","ava johnson","noah williams","liam davis","zoe martinez","ethan brown"]):
    """
    Checking the database if we have availability for the specific specialist.
    The parameters should be mentioned by the user in the query
    """
    #Dummy data
    df = pd.read_csv(f"{WORKDIR}/data/syntetic_data/availability.csv")
    df['date_slot_time'] = df['date_slot'].apply(lambda input: input.split(' ')[-1])
    rows = list(df[(df['date_slot'].apply(lambda input: input.split(' ')[0]) == desired_date.date)&(df['specialist_name'] == specialist_name)&(df['is_available'] == True)]['date_slot_time'])

    if len(rows) == 0:
        output = "No availability in the entire day"
    else:
        output = f'This availability for {desired_date.date}\n'
        output += "Available slots: " + ', '.join(rows)

    return output

@tool
def check_availability_by_service (desired_date:DateModel, service:Literal["hairstylist","nail_technician","esthetician","makeup_artist","massage_therapist","eyebrow_specialist","colorist"]):
    """
    Checking the database if we have availability for the specific service.
    The parameters should be mentioned by the user in the query
    """
    #Dummy data
    df = pd.read_csv(f"{WORKDIR}/data/syntetic_data/availability.csv")
    df['date_slot_time'] = df['date_slot'].apply(lambda input: input.split(' ')[-1])
    rows = df[(df['date_slot'].apply(lambda input: input.split(' ')[0]) == desired_date.date) & (df['service'] == service) & (df['is_available'] == True)].groupby(['service', 'specialist_name'])['date_slot_time'].apply(list).reset_index(name='available_slots')

    if len(rows) == 0:
        output = "No availability in the entire day"
    else:
        output = f'This availability for {desired_date.date}\n'
        for row in rows.values:
            output += row[1] + ". Available slots: " + ', '.join(row[2])+'\n'

    return output

@tool
def reschedule_booking (old_date:DateTimeModel, new_date:DateTimeModel, id_number:IdentificationNumberModel, specialist_name:Literal["emma thompson","olivia parker","sophia chen","mia rodriguez","isabella kim","ava johnson","noah williams","liam davis","zoe martinez","ethan brown"]):
    """
    Rescheduling an appointment.
    The parameters MUST be mentioned by the user in the query.
    """
    #Dummy data
    df = pd.read_csv(f'{WORKDIR}/data/syntetic_data/availability.csv')
    available_for_desired_date = df[(df['date_slot'] == new_date.date)&(df['is_available'] == True)&(df['specialist_name'] == specialist_name)]
    if len(available_for_desired_date) == 0:
        return "Not available slots in the desired period"
    else:
        cancel_appointment.invoke({'date':old_date, 'id_number':id_number, 'specialist_name':specialist_name})
        set_appointment.invoke({'desired_date':new_date, 'id_number': id_number, 'specialist_name': specialist_name})
        return "Succesfully rescheduled for the desired time"

@tool
def cancel_booking(date: DateTimeModel, id_number: IdentificationNumberModel, specialist_name: Literal["emma thompson", "olivia parker", "sophia chen", "mia rodriguez", "isabella kim", "ava johnson", "noah williams", "liam davis", "zoe martinez", "ethan brown"]):
    """
    Canceling an appointment.
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
        
        return "Successfully cancelled"

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
def book_appointment(desired_date:DateTimeModel, id_number:IdentificationNumberModel, specialist_name:Literal["emma thompson","olivia parker","sophia chen","mia rodriguez","isabella kim","ava johnson","noah williams","liam davis","zoe martinez","ethan brown"]):
    """
    Set appointment with the specialist.
    The parameters MUST be mentioned by the user in the query.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Attempting to set appointment with parameters: date={desired_date.date}, id={id_number.id}, specialist={specialist_name}")
    try:
        df = pd.read_csv(f'{WORKDIR}/data/syntetic_data/availability.csv')
        logger.info(f"Availability data loaded. Shape: {df.shape}")
        
        case = df[(df['date_slot'] == desired_date.date) & (df['specialist_name'] == specialist_name) & (df['is_available'] == True)]
        logger.info(f"Matching cases found: {len(case)}")
        
        if len(case) == 0:
            logger.warning("No available appointments for the specified case")
            return "No available appointments for that particular case"
        else:
            client_id = int(id_number.id) if isinstance(id_number.id, str) else id_number.id
            logger.info(f"Setting appointment for client ID: {client_id}")
            
            df.loc[(df['date_slot'] == desired_date.date) & (df['specialist_name'] == specialist_name) & (df['is_available'] == True), ['is_available','client_to_attend']] = [False, float(client_id)]
            
            df.to_csv(f'{WORKDIR}/data/syntetic_data/availability.csv', index=False)
            logger.info("Appointment set successfully")
            
            return f"Appointment successfully set for {desired_date.date} with Dr. {specialist_name} for client ID {client_id}"
    except ValueError as ve:
        logger.error(f"ValueError in set_appointment: {str(ve)}")
        return f"Invalid ID number: {str(ve)}"
    except Exception as e:
        logger.error(f"Exception in set_appointment: {str(e)}")
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
        return "The client doesn´t have any study made"
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
        return "The client doesn´t have any appointment yet"
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