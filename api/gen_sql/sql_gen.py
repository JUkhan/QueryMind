import os
import re
import sqlite3
import sys
import threading

from typing import Annotated, Sequence
from typing_extensions import TypedDict

from pydantic import BaseModel, Field

from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages, REMOVE_ALL_MESSAGES
from langgraph.prebuilt import ToolNode

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gen_sql.schema import (
    SCHEMA_FILE,
    get_schema,
    extract_table_names,
    filter_schemas_by_table_names,
)
from gen_sql.usage import UsageTracker, find_tracker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_NAME = os.getenv('GEN_SQL_MODEL', 'gemini-3.5-flash-lite')

# Messages retained per thread. The window is always cut back to a HumanMessage
# so a tool call never gets separated from its result (Gemini rejects that).
MAX_HISTORY_MESSAGES = 20

# Supersteps per turn: agent -> tools -> agent counts as 3, so this allows a
# handful of schema lookups before the turn is abandoned.
RECURSION_LIMIT = 12


class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def db_system():
    """Read DB_SYSTEM at call time; at import time load_dotenv() may not have run."""
    return os.getenv('DB_SYSTEM', 'sqlite')


_llm = None
_tools_model = None
# Reentrant: get_tools_model() holds the lock while calling get_llm().
_model_lock = threading.RLock()


def get_llm():
    """Build the chat model on first use so a missing API key fails the request, not app boot."""
    global _llm
    if _llm is None:
        with _model_lock:
            if _llm is None:
                _llm = init_chat_model(
                    model=MODEL_NAME, temperature=0, model_provider='google_genai')
    return _llm


def get_tools_model():
    global _tools_model
    if _tools_model is None:
        with _model_lock:
            if _tools_model is None:
                _tools_model = get_llm().bind_tools(tools)
    return _tools_model


_schema_cache = {'mtime': None, 'schema': None, 'table_names': None}


def load_schema():
    """Return (schema_text, table_name_summary), re-reading schema.txt only when it changes."""
    try:
        mtime = os.path.getmtime(SCHEMA_FILE)
    except OSError as exc:
        print(f'Could not read schema file {SCHEMA_FILE}: {exc}')
        return None, None

    if _schema_cache['mtime'] != mtime:
        schema = get_schema(SCHEMA_FILE)
        _schema_cache.update(
            mtime=mtime, schema=schema, table_names=extract_table_names(schema))
    return _schema_cache['schema'], _schema_cache['table_names']


class TableSelection(BaseModel):
    """Tables required to answer a query description."""

    table_names: list[str] = Field(
        description='Exact table names copied from the provided list, no extra text.')


@tool
def get_schema_detail(query_description: str, config: RunnableConfig = None) -> str:
    """This is a schema detail function that generates appropriate schema based on the query description"""

    schema, table_summary = load_schema()
    if not schema:
        return 'The database schema is unavailable, so no query can be generated.'

    system_message = SystemMessage(
        content='you are my assistant, please answer my question to the best of your ability.')
    human_message = HumanMessage(content=f"""
     Given this database table names with description([tableName] - [description]):
    ```
    {table_summary}
    default -
    ```
    Find expected table names that would be used to create sql query using the following query description:
    {query_description}
    """)

    # Structured output instead of parsing prose: a preamble like "Here are the
    # tables: orders" used to be split on ',' and silently match nothing.
    # config is injected by the tool runtime, never by the model. Forwarding it
    # is what puts this call under the run's callbacks: without it the schema
    # lookup's tokens go uncounted, one missing call per lookup.
    try:
        selection = get_llm().with_structured_output(TableSelection).invoke(
            [system_message, human_message], config=config)
    except Exception as exc:
        print(f'Table selection failed: {exc}')
        return 'The schema lookup failed. Ask the user to try again.'

    tables = getattr(selection, 'table_names', None) or []
    print('TABLES::', tables)
    filtered = filter_schemas_by_table_names(','.join(tables), schema)

    if not filtered:
        return 'Your query description is not sufficient to generate a valid query.'
    return filtered


tools = [get_schema_detail]


def message_text(message):
    """Extract plain text from message content, handling both string and list formats."""
    content = getattr(message, 'content', message)
    if isinstance(content, list):
        # Extract text from all text blocks (new format with thought signatures)
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get('type') == 'text':
                text_parts.append(block.get('text', ''))
            elif isinstance(block, str):
                text_parts.append(block)
        return ' '.join(text_parts)
    return content if isinstance(content, str) else ''


# Kept under the old name: other modules and notebooks import it.
extract_message_content = message_text


def system_prompt():
    return f"""
  You are my AI assistant, please answer my query to the best of your ability.
  call get_schema_detail tool if you do not have enough schema to generate {db_system()} query.
  When writing SQL queries with aggregate functions, always assign meaningful alias names to aggregated columns using AS. For example: SELECT COUNT(*) AS total_records, AVG(price) AS average_price, SUM(quantity) AS total_quantity FROM table_name.
  Always return the final query inside a ```sql code fence.
  Only response on query generation.
  """


def window_start(messages):
    """First index to keep, moved back to a HumanMessage so tool pairs stay intact.

    MAX_HISTORY_MESSAGES is a target rather than a hard cap: aligning the cut to
    a turn boundary can retain a few extra messages, at most one turn's worth
    (which RECURSION_LIMIT bounds).
    """
    if len(messages) <= MAX_HISTORY_MESSAGES:
        return 0
    idx = len(messages) - MAX_HISTORY_MESSAGES
    while idx > 0 and not isinstance(messages[idx], HumanMessage):
        idx -= 1
    return idx


def last_question(messages):
    """The most recent real user question, skipping the control words."""
    for message in reversed(messages):
        if not isinstance(message, HumanMessage):
            continue
        text = message_text(message).strip()
        if text and text.lower() not in ('retry', 'new conversation'):
            return text
    return None


def agent(state: State, config: RunnableConfig = None):
    messages = list(state['messages'])
    last = messages[-1] if messages else None
    # isinstance first: Gemini returns list content, which has no .strip().
    command = message_text(last).strip().lower() if isinstance(last, HumanMessage) else ''

    if command == 'new conversation':
        # A plain list.clear() does not survive the add_messages reducer, which
        # only appends or replaces by id. RemoveMessage is the reducer's own
        # delete protocol.
        return {'messages': [RemoveMessage(id=REMOVE_ALL_MESSAGES),
                             AIMessage('New conversation started')]}

    dropped = []
    if command == 'retry':
        question = last_question(messages)
        if question is not None:
            # Clear the stored history too, otherwise the tools -> agent hop
            # rebuilds the very context the retry was meant to discard.
            messages = [HumanMessage(question)]
            dropped = [RemoveMessage(id=REMOVE_ALL_MESSAGES), messages[0]]

    if not dropped:
        start = window_start(messages)
        dropped = [RemoveMessage(id=m.id) for m in messages[:start] if m.id]
        messages = messages[start:]
        if start:
            tracker = find_tracker(config)
            if tracker:
                tracker.note_trim(start)

    response = get_tools_model().invoke([('system', system_prompt())] + messages)
    return {'messages': dropped + [response]}


def should_continue(state: State):
    last_message = state['messages'][-1]

    if not getattr(last_message, 'tool_calls', None):
        return 'end'
    return 'continue'


def build_checkpointer():
    """Persist threads to SQLite; the worker recycles every ~1000 requests."""
    path = os.getenv('CHECKPOINT_DB', os.path.join(BASE_DIR, 'checkpoints.db'))
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        connection = sqlite3.connect(path, check_same_thread=False)
        saver = SqliteSaver(connection)
        saver.setup()
        print(f'Chat history checkpointed to {path}')
        return saver
    except Exception as exc:
        print(f'Falling back to in-memory chat history ({exc}); '
              'conversations will be lost when the worker restarts.')
        return InMemorySaver()


graph = StateGraph(State)

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
        'end': END
    }
)

graph.add_edge('tools', 'agent')

graph_app = graph.compile(checkpointer=build_checkpointer())


def thread_config(thread_id, callbacks=None):
    if not thread_id:
        # Defaulting to a shared id put every client without a thread into one
        # conversation, leaking history between users.
        raise ValueError('thread_id is required')
    config = {
        'configurable': {'thread_id': str(thread_id)},
        'recursion_limit': RECURSION_LIMIT,
    }
    if callbacks:
        # Run level: LangChain hands these down to every LLM call the run makes,
        # including the one inside get_schema_detail once the tool forwards its
        # config. Kept out of 'configurable' because that is checkpointed and a
        # handler does not serialise.
        config['callbacks'] = list(callbacks)
    return config


def rollback_turn(config):
    """Drop the messages a failed turn left behind so the thread stays usable."""
    try:
        state = graph_app.get_state(config)
        messages = list(state.values.get('messages', [])) if state.values else []
        cut = len(messages)
        while cut > 0 and not isinstance(messages[cut - 1], HumanMessage):
            cut -= 1
        if cut == 0:
            return
        removals = [RemoveMessage(id=m.id) for m in messages[cut - 1:] if m.id]
        if removals:
            graph_app.update_state(config, {'messages': removals})
    except Exception as exc:
        print(f'Could not roll back failed turn: {exc}')


# The language tag is optional; \b keeps `sql` from matching the `sql` prefix of
# `sqlite` and leaving `ite` in the query.
SQL_FENCE = re.compile(
    r'```(?:(?:sql|sqlite|postgresql|postgres|mysql|mssql|tsql)\b)?\s*([\s\S]*?)\s*```',
    re.IGNORECASE)


def extract(text):
    if isinstance(text, list):
        text = ''.join(str(part) for part in text)

    match = SQL_FENCE.search(text or '')

    if not match or not match.group(1):
        return text

    return match.group(1).strip()


def get_messages(thread_id):
    if not thread_id:
        return []

    config = thread_config(thread_id)
    current_state = graph_app.get_state(config)
    if not current_state.values:
        return []

    messages = current_state.values['messages']
    messages = [msg for msg in messages
                if not (isinstance(msg, (SystemMessage, ToolMessage)) or not msg.content)]
    res = []

    for msg in messages:
        if isinstance(msg, HumanMessage):
            res.append({'text': message_text(msg), 'sender': 'user'})
        else:
            res.append({'text': extract(message_text(msg)), 'sender': 'bot'})
    return res


def run_chatbot(user_input, thread_id):
    tracker = UsageTracker(thread_id)
    config = thread_config(thread_id, callbacks=[tracker])
    # Only the new message goes in: the checkpointer restores the rest, and
    # re-sending the stored list made every trim silently reappear.
    try:
        response = graph_app.invoke({'messages': [HumanMessage(user_input)]}, config=config)
    except GraphRecursionError:
        print(f'Recursion limit hit for thread {thread_id}')
        rollback_turn(config)
        return 'I could not finish generating that query. Please rephrase it and try again.'
    except Exception:
        # The question is checkpointed before the node runs; drop it so a failed
        # turn (rate limit, network) does not leave an unanswered message behind.
        rollback_turn(config)
        raise
    finally:
        # An abandoned turn still spent its tokens, and a turn that burned the
        # recursion limit spent the most of any.
        tracker.log()

    return message_text(response['messages'][-1])


def run_chatbot_test(user_input, thread_id):
    """Local debugging helper: streams each step and returns the final text."""
    tracker = UsageTracker(thread_id, label='test')
    config = thread_config(thread_id, callbacks=[tracker])
    output = ''
    try:
        for step in graph_app.stream({'messages': [HumanMessage(user_input)]},
                                     config, stream_mode='values'):
            message = step['messages'][-1]
            output = message_text(message)
            message.pretty_print()
    finally:
        tracker.log()
    return output
