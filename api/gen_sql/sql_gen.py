import os
import re
#from dotenv import load_dotenv
from typing import Annotated, Sequence
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain.chat_models import init_chat_model
#from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage,AIMessage, SystemMessage, BaseMessage, ToolMessage
from typing_extensions import TypedDict
#from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
#from langgraph.types import Command, interrupt
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gen_sql.schema import  get_schema, extract_table_names, filter_schemas_by_table_names
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

db_system=os.getenv('DB_SYSTEM', 'sqlite')

class State(TypedDict):
  messages: Annotated[Sequence[BaseMessage], add_messages]

llm = init_chat_model(model="gemini-3.5-flash", temperature=0, model_provider='google_genai')

@tool
def get_schema_detail(query_description: str):
  """This is a schema detail function that generates appropriate schema based on the query description"""
  
  system_message = SystemMessage(content="you are my assistant, please answer my question to the best of your ability.")
  human_message = HumanMessage(content=f"""
     Given this database table names with description([tableName] - [description]):
    ```
    {extract_table_names(get_schema())}
    default -
    ```
    Find expected table names that would be used to create sql query using the following query description:
    {query_description}

    Please provide only the comma separated table names without any explanations.
    """)  
                        
  reply = llm.invoke([system_message, human_message])
  tables = extract_message_content(reply)
  print('TABLES::',tables)
  schema = filter_schemas_by_table_names(tables, get_schema())
 
  if not schema:
    return 'Your query description is not sufficient to generate a valid query.'
  return schema


tools=[get_schema_detail]

tools_model = llm.bind_tools(tools)

def agent(state: State):
  system_message=f"""
  You are my AI assistant, please answer my query to the best of your ability.
  call get_schema_detail tool if you do not have enough schema to generate {db_system} query.
  When writing SQL queries with aggregate functions, always assign meaningful alias names to aggregated columns using AS. For example: SELECT COUNT(*) AS total_records, AVG(price) AS average_price, SUM(quantity) AS total_quantity FROM table_name.
  Only response on query generation.
  """
  messages = list(state['messages'])
  last_message = messages[-1].content.strip().lower()
  if last_message == 'new conversation':
     state['messages'].clear()
     state['messages'].append(AIMessage('New conversation started'))
     return state
  if last_message == 'retry':
     for it in messages[::-1]:
        if it.content.strip().lower() !='retry' and isinstance(it, HumanMessage):
           messages=[it]
           break
     
  response=tools_model.invoke([('system', system_message)] + messages)
  # if hasattr(response, 'tool_calls') and response.tool_calls:
  #    print(f'USING TOOLS: {[tc['name'] for tc in response.tool_calls]}')

  state['messages']=[response]
  return state

def should_continue(state:State):
  messages=state['messages']
  last_message = messages[-1]

  if not last_message.tool_calls:
    return 'end'
  return 'continue'

graph=StateGraph(State)

graph.add_node('agent', agent)

tool_node = ToolNode(tools=tools)

graph.add_node('tools', tool_node)

# edges

graph.add_edge(START, 'agent')

graph.add_conditional_edges(
  'agent',
  should_continue,
  {
    'continue': 'tools',
    'end':END
  }
)

graph.add_edge('tools', 'agent')

print("Graph nodes:", graph.nodes.keys())
app = graph.compile(checkpointer=InMemorySaver())

output=''
def extract_message_content(message):
    """Extract plain text from message content, handling both string and list formats."""
    content = message.content
    if isinstance(content, list):
        # Extract text from all text blocks (new format with thought signatures)
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get('type') == 'text':
                text_parts.append(block.get('text', ''))
            elif isinstance(block, str):
                text_parts.append(block)
        return ' '.join(text_parts)
    return content
def print_stream(stream):
    global output
    for s in stream:
        message = s['messages'][-1]
        output=message.content
        if isinstance(message, tuple):
            print(message)
        else:
            message.pretty_print()


def run_chatbot_test(user_input, thread_id):
    if not thread_id:
        thread_id = "1"
    
    config = {"configurable": {"thread_id": thread_id}}
    current_state = app.get_state(config)
    # Initialize state if it doesn't exist
    if not current_state.values:
        initial_state = {
            "messages": []
        }
    else:
        initial_state = current_state.values

    user_message = ('human', user_input)
    initial_state["messages"].append(user_message)
    print_stream(app.stream(initial_state, config, stream_mode='values'))
    return output

def extract(text):
    json_regex = r'```(?:sqlite|sql|postgresql)\s*([\s\S]*?)\s*```'
    if(isinstance(text, list)):
        text = "".join(text)
    match = re.search(json_regex, text)
    
    if not match:
        return text
    
    if not match.group(1):
        return text
    
    return match.group(1).strip()

def get_messages(thread_id):
   print('db_system: ', db_system)
   if not thread_id:
        return []
   print(thread_id)
   config = {"configurable": {"thread_id": thread_id}}
   current_state = app.get_state(config)
   if not current_state.values:
      return []
   
   messages=current_state.values['messages']
   messages=[msg for msg in messages if not (isinstance(msg, SystemMessage) or isinstance(msg, ToolMessage) or not msg.content)]
   res=[]
   
   for msg in messages:
      if isinstance(msg, HumanMessage):
        res.append({'text':extract_message_content(msg), 'sender': 'user' })
      else:
         res.append({'text':extract(extract_message_content(msg)), 'sender': 'bot' })
   return res

def run_chatbot(user_input, thread_id):
    if not thread_id:
        thread_id = "1"
    print("user input:", user_input)
    config = {"configurable": {"thread_id": thread_id}}
    current_state = app.get_state(config)
    # Initialize state if it doesn't exist
    if not current_state.values:
        initial_state = {
            "messages": []
        }
    else:
        initial_state = current_state.values
    if(len(initial_state['messages']) >= 10):
        del initial_state['messages'][5:]
    user_message = ('human', user_input)
    initial_state["messages"].append(user_message)
    response = app.invoke(initial_state, config=config)
    print("len:", len(response["messages"]), 'last content:',response["messages"][-1].content)
    query = extract_message_content(response["messages"][-1])
    if(isinstance(query, list)):
        return "".join(query)
    return query