import os
import sys

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from src.vector_database.utils import PineconeManagment

load_dotenv()

def reinitialize_vectordatabase(index_name):
    vdb_app = PineconeManagment()
    vdb_app.reinitialize_database(index_name)

if __name__ == '__main__':
    reinitialize_vectordatabase(index_name='zenbeautysalon')