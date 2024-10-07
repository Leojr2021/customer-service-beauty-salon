from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_anthropic import ChatAnthropic
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from typing import Literal
from datetime import datetime, timedelta

def format_retrieved_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def get_model(provider:Literal['openai','google','meta','anthropic']):
    if provider == "openai":
        return ChatOpenAI(temperature=0, model_name="gpt-4o-mini")  # Remove strict=True
    elif provider == "anthropic":
        return ChatAnthropic(temperature=0, model_name="claude-3-5-sonnet")
    elif provider == "google":
        return ChatGoogleGenerativeAI(temperature=0, model_name="gemini-1.5-pro-exp-0801")
    elif provider == "meta":
        return ChatGroq(temperature=0, model_name="llama-3.1-70b-versatile")
