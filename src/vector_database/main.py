import os
from dotenv import load_dotenv
import sys

load_dotenv()
WORKDIR=os.getenv("WORKDIR")
os.chdir(WORKDIR)
sys.path.append(WORKDIR)

from src.vector_database.utils import PineconeManagment

def reinitialize_vectordatabase(index_name):
    vdb_app = PineconeManagment()
    vdb_app.reinitialize_database(index_name)

if __name__ == '__main__':
    reinitialize_vectordatabase(index_name='zenbeautysalon')