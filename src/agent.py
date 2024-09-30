import os
from dotenv import load_dotenv
import sys
import gradio as gr

load_dotenv()
WORKDIR=os.getenv("WORKDIR")
os.chdir(WORKDIR)
sys.path.append(WORKDIR)

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated, List, Literal
from langchain_core.messages import AnyMessage, HumanMessage
import operator
from src.validators.agent_validators import *
from src.agent_tools import check_availability_by_specialist, check_availability_by_service, check_results, book_appointment, cancel_booking, reminder_appointment, reschedule_booking, retrieve_faq_info, get_salon_services, get_specialist_services
from datetime import datetime, timedelta
from src.utils import get_model
import logging
import logging_config

# Set up file logging
logging.basicConfig(filename='ai_responses.log', level=logging.INFO, 
                    format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class MessagesState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]

tools = [check_availability_by_specialist, check_availability_by_service, check_results, book_appointment, cancel_booking, reminder_appointment, reschedule_booking, retrieve_faq_info, get_salon_services, get_specialist_services]

tool_node = ToolNode(tools)

model = get_model('openai')
model = model.bind_tools(tools=tools)

def should_continue(state: MessagesState) -> Literal["tools", "human_feedback"]:
    messages = state['messages']
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "human_feedback"

def should_continue_with_feedback(state: MessagesState) -> Literal["agent", "end"]:
    messages = state['messages']
    last_message = messages[-1]
    if isinstance(last_message, dict):
        if last_message.get("type","") == 'human':
            return "agent"
    if (isinstance(last_message, HumanMessage)):
        return "agent"
    return "end"

def call_model(state: MessagesState):
    messages = [SystemMessage(content=f"You are helpful assistant in Zen Beauty Salon, a Beauty Salon in California (United States).\nAs reference, today is {datetime.now().strftime('%Y-%m-%d %H:%M, %A')}.\nKeep a friendly, professional tone.\nAvoid verbosity.\nConsiderations:\n- Don´t assume parameters in call functions that it didnt say.\n- MUST NOT force users how to write. Let them write in the way they want.\n- The conversation should be very natural like a secretary talking with a client.\n- Call only ONE tool at a time.")] + state['messages']
    response = model.invoke(messages)
    logger.info(f"Full model response: {response}")
    if response.additional_kwargs.get('tool_calls'):
        for tool_call in response.additional_kwargs['tool_calls']:
            logger.info(f"Tool call: {tool_call}")
    return {"messages": [response]}

def read_human_feedback(state: MessagesState):
    pass

workflow = StateGraph(MessagesState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_node("human_feedback", read_human_feedback)
workflow.set_entry_point("agent")

def should_continue(state):
    last_message = state["messages"][-1]
    if isinstance(last_message, HumanMessage):
        return "agent"
    if "tool_calls" in last_message.additional_kwargs:
        return "tools"
    return "human_feedback"

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "agent": "agent",
        "tools": "tools",
        "human_feedback": "human_feedback"
    }
)

workflow.add_conditional_edges(
    "human_feedback",
    should_continue_with_feedback,
    {
        "agent": 'agent',
        "end": END
    }
)

workflow.add_edge("tools", 'agent')

checkpointer = MemorySaver()

app = workflow.compile(checkpointer=checkpointer, 
                       interrupt_before=['human_feedback'])

# Gradio chat function
def chat_with_ai(message, history=[]):
    state = {"messages": [HumanMessage(content=msg) for _, msg in history]}
    state = app.invoke(
        {
            "messages": state["messages"] + [HumanMessage(content=message)]
        },
        config={
            "configurable": {"thread_id": 42},
            "recursion_limit": 100  # Increased from 50 to 100
        }
    )
    ai_response = state["messages"][-1].content
    
    # Log the conversation
    logger.info(f"User: {message}")
    logger.info(f"AI: {ai_response}")
    
    return ai_response

# Gradio interface
iface = gr.ChatInterface(
    chat_with_ai,
    chatbot=gr.Chatbot(height=300),
    textbox=gr.Textbox(placeholder="Type your message here...", container=False, scale=7),
    title="Zen Beauty Salon Assistant",
    description="Welcome to Zen Beauty Salon's  Assistant. How may I assist you today?",
    theme="soft",
    examples=["What services do you offer?", "Can I book an appointment?", "What are your operating hours?"],
    cache_examples=False,
    retry_btn=None,
    undo_btn="Delete Previous",
    clear_btn="Clear",
)

# Launch the Gradio interface
if __name__ == "__main__":
    iface.launch()