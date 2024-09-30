import os
from dotenv import load_dotenv
import sys
from zoneinfo import ZoneInfo

load_dotenv()
WORKDIR = os.getenv("WORKDIR")
os.chdir(WORKDIR)
sys.path.append(WORKDIR)

import csv
from datetime import datetime, timedelta
import random

# Define the data structure
data = [
    {"specialization": "hairstylist", "specialists": [{"name": "emma thompson"}, {"name": "olivia parker"}]},
    {"specialization": "nail_technician", "specialists": [{"name": "sophia chen"}, {"name": "mia rodriguez"}]},
    {"specialization": "esthetician", "specialists": [{"name": "isabella kim"}]},
    {"specialization": "makeup_artist", "specialists": [{"name": "ava johnson"}]},
    {"specialization": "massage_therapist", "specialists": [{"name": "noah williams"}, {"name": "liam davis"}]},
    {"specialization": "eyebrow_specialist", "specialists": [{"name": "zoe martinez"}]},
    {"specialization": "colorist", "specialists": [{"name": "ethan brown"}]},
]


# Function to generate time slots
def generate_time_slots(start_time, end_time, interval_minutes):
    TIMEZONE = os.getenv('TIMEZONE', 'America/New_York')
    current_time = start_time.replace(tzinfo=ZoneInfo(TIMEZONE))
    end_time = end_time.replace(tzinfo=ZoneInfo(TIMEZONE))
    time_slots = []
    while current_time < end_time:
        time_slots.append(current_time.strftime("%Y-%m-%d %H:%M"))
        current_time += timedelta(minutes=interval_minutes)
    return time_slots


# Generate CSV data
def generate_csv(filename):
    # Get the current date
    current_date = datetime.now().date()
    start_date = datetime(current_date.year, current_date.month, current_date.day)

    # Define the time slots for two weeks
    time_slots = []
    for day in range(14):  # Covering two weeks
        date = start_date + timedelta(days=day)
        if date.weekday() < 5:  # Monday to Friday
            time_slots += generate_time_slots(
                datetime(date.year, date.month, date.day, 8, 0),
                datetime(date.year, date.month, date.day, 17, 0),
                30,
            )
        elif date.weekday() == 5:  # Saturday
            time_slots += generate_time_slots(
                datetime(date.year, date.month, date.day, 9, 0),
                datetime(date.year, date.month, date.day, 13, 0),
                30,
            )

    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["date_slot", "specialization", "specialist_name", "is_available", "client_to_attend"])

        for specialization in data:
            for specialist in specialization["specialists"]:
                for slot in time_slots:
                    # Ensure at least 50% availability for each specialist
                    is_available = random.choice([True] * 5 + [False] * 5)
                    client_to_attend = None if is_available else random.randint(1000000, 1000100)
                    writer.writerow([slot, specialization["specialization"], specialist["name"], is_available, client_to_attend])

if __name__ == '__main__':
    generate_csv(f"{WORKDIR}/data/syntetic_data/availability.csv")