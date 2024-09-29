import os
from dotenv import load_dotenv
import sys
import time
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import JSONLoader  
from langchain_core.documents import Document 
from pinecone import Pinecone, ServerlessSpec
from typing import Dict
import logging

load_dotenv()
WORKDIR = os.getenv("WORKDIR")
os.chdir(WORKDIR)
sys.path.append(WORKDIR)

from src.validators.pinecone_validators import IndexNameStructure, ExpectedNewData

logger = logging.getLogger(__name__)

class PineconeManagment:
    def __init__(self):
        logger.info("Setting pinecone connection...")
        self.pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

    def __extract_metadata(self, record: dict, metadata: dict) -> dict:
        metadata["question"] = record['question']
        logger.info("Metadata extracted!")
        return metadata

    def reading_datasource(self):
        loader = JSONLoader(
            file_path=f'{WORKDIR}/faq/data.json',
            jq_schema='.[]',
            text_content=False,
            metadata_func=self.__extract_metadata)

        return loader.load()
    
    def creating_index(self, index_name: str, docs: Document, dimension=1536, metric="cosine", embedding = OpenAIEmbeddings(model="text-embedding-ada-002")):
        logger.info(f"Creating index {index_name}...")
        IndexNameStructure(index_name=index_name)
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
        if index_name in existing_indexes:
            raise Exception("The index already exists...")
        pc.create_index(
            name=index_name.lower(),
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

        while not pc.describe_index(index_name).status["ready"]:
            time.sleep(1)

        logger.info(f"Index '{index_name}' created...")
        
        PineconeVectorStore.from_documents(documents = docs, embedding = embedding, index_name = index_name)

        logger.info(f"Index '{index_name}' populated with data...")
        
    def loading_vdb(self, index_name: str, embedding=OpenAIEmbeddings(model="text-embedding-3-small")):
        logger.info("Loading vector database from Pinecone...")
        self.vdb =  PineconeVectorStore(index_name=index_name, embedding=embedding)
        logger.info("Vector database loaded...")
    

    def adding_documents(self, new_info: Dict[str,str]):
        ExpectedNewData(new_info = new_info)
        logger.info("Adding data in the vector database...")
        self.vdb.add_documents([Document(page_content="question: " + new_info['question'] + '\n answer: ' + new_info['answer'], metadata={"question": new_info['question']})])
        logger.info("More info added in the vector database...")

    def finding_similar_docs(self, user_query):
        docs = self.vdb.similarity_search_with_relevance_scores(
            query=user_query,
            k=5,  # Increase from 3 to 5
            score_threshold=0.7  # Lower from 0.9 to 0.7
        )
        
        if not docs:
            return [("I couldn't find an exact match to your question. Here's some general information that might help:", 1.0)]
        
        return docs

    def reinitialize_database(self, index_name: str):
        logger.info(f"Reinitializing database for index: {index_name}")
        
        # Step 1: Delete existing index if it exists
        existing_indexes = [index_info["name"] for index_info in self.pc.list_indexes()]
        if index_name in existing_indexes:
            logger.info(f"Deleting existing index: {index_name}")
            self.pc.delete_index(index_name)
            time.sleep(10)  # Wait for the deletion to complete
        
        # Step 2: Create new index
        logger.info(f"Creating new index: {index_name}")
        self.creating_index(index_name, [], dimension=1536, metric="cosine")
        
        # Step 3: Load FAQ data
        logger.info("Loading FAQ data")
        docs = self.reading_datasource()
        
        # Step 4: Add data to the new index
        logger.info("Adding FAQ data to the new index")
        embedding = OpenAIEmbeddings(model="text-embedding-3-small")
        PineconeVectorStore.from_documents(documents=docs, embedding=embedding, index_name=index_name)
        
        logger.info(f"Database reinitialization complete for index: {index_name}")

