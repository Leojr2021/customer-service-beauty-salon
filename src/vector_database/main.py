from dotenv import load_dotenv
from src.vector_database.utils import PineconeManagment

load_dotenv()

def reinitialize_vectordatabase(index_name):
    vdb_app = PineconeManagment()
    vdb_app.reinitialize_database(index_name)

if __name__ == '__main__':
    reinitialize_vectordatabase(index_name='zenbeautysalon')