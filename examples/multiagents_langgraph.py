"""
Multi-Agent Workflow Example — LangGraph + Claude Sonnet 5
=============================================================

This mirrors the OpenAI Agents SDK sample, rebuilt with LangGraph:
  - A Guardrail node that blocks off-topic requests before routing
  - A Supervisor (triage) node that decides which specialist handles the turn
  - A Billing Agent node with a tool (order lookup)
  - A Technical Support Agent node
  - Conditional edges that wire the routing logic into an explicit graph

All nodes run on Anthropic's Claude Sonnet 5 model (`claude-sonnet-5`)
via `langchain-anthropic`.

--------------------------------------------------------------------
SETUP
--------------------------------------------------------------------
1. Install dependencies:

       pip install langgraph langchain-anthropic langchain-core pydantic

2. Set your Anthropic API key as an environment variable:

       export ANTHROPIC_API_KEY="sk-ant-..."

3. Run:

       python multi_agent_langgraph.py
--------------------------------------------------------------------
"""

import os
from typing import Annotated, Literal, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, create_react_agent
from pydantic import BaseModel, Field

if not os.environ.get("ANTHROPIC_API_KEY"):
    raise RuntimeError(
        "Set the ANTHROPIC_API_KEY environment variable before running this script."
    )

MODEL_ID = "claude-sonnet-5"


def claude_model(**kwargs) -> ChatAnthropic:
    """Factory so every node gets its own ChatAnthropic instance bound to Sonnet 5."""
    return ChatAnthropic(model=MODEL_ID, temperature=0, **kwargs)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@tool
def lookup_order(order_id: str) -> str:
    """Look up the status of a customer order by its order ID, e.g. 'ORD-1042'."""
    fake_orders = {
        "ORD-1042": "Shipped — arriving Aug 29, 2026.",
        "ORD-2077": "Processing — payment confirmed, not yet shipped.",
        "ORD-3090": "Delivered on Aug 20, 2026.",
    }
    return fake_orders.get(order_id, f"No order found with ID {order_id}.")


# ---------------------------------------------------------------------------
# Shared graph state
# ---------------------------------------------------------------------------
class GraphState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    next_agent: str  # set by the supervisor / guardrail
    blocked: bool


# ---------------------------------------------------------------------------
# Guardrail node: keep the system on-topic (customer support only)
# ---------------------------------------------------------------------------
class TopicCheck(BaseModel):
    is_off_topic: bool = Field(description="True if the request is unrelated to customer support")
    reasoning: str


def guardrail_node(state: GraphState) -> GraphState:
    checker = claude_model().with_structured_output(TopicCheck)
    last_user_msg = state["messages"][-1].content
    result: TopicCheck = checker.invoke(
        [
            SystemMessage(
                content=(
                    "Determine whether the user's message is a customer-support "
                    "request (billing, orders, account, technical issues). If it "
                    "is clearly unrelated (creative writing, homework, trivia), "
                    "mark it as off-topic."
                )
            ),
            HumanMessage(content=last_user_msg),
        ]
    )
    if result.is_off_topic:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "I can only help with customer-support requests "
                        "(billing, orders, technical issues). Could you "
                        "rephrase your request?"
                    )
                )
            ],
            "blocked": True,
            "next_agent": "end",
        }
    return {"blocked": False, "next_agent": ""}


def route_after_guardrail(state: GraphState) -> Literal["supervisor", "end"]:
    return "end" if state["blocked"] else "supervisor"


# ---------------------------------------------------------------------------
# Supervisor (triage) node — decides which specialist handles the turn
# ---------------------------------------------------------------------------
class RouteDecision(BaseModel):
    destination: Literal["billing", "technical", "general"] = Field(
        description="Which specialist should handle this request"
    )


def supervisor_node(state: GraphState) -> GraphState:
    router = claude_model().with_structured_output(RouteDecision)
    last_user_msg = state["messages"][-1].content
    decision: RouteDecision = router.invoke(
        [
            SystemMessage(
                content=(
                    "Route the customer's message to the right specialist:\n"
                    "- 'billing' for payments, refunds, or order status\n"
                    "- 'technical' for bugs or product issues\n"
                    "- 'general' if neither clearly applies"
                )
            ),
            HumanMessage(content=last_user_msg),
        ]
    )
    return {"next_agent": decision.destination}


def route_after_supervisor(state: GraphState) -> Literal["billing", "technical", "general"]:
    return state["next_agent"]


# ---------------------------------------------------------------------------
# Specialist agents (prebuilt ReAct agents from LangGraph)
# ---------------------------------------------------------------------------
billing_agent = create_react_agent(
    model=claude_model(),
    tools=[lookup_order],
    prompt=(
        "You are a billing support specialist. Help with charges, refunds, "
        "invoices, and order status. Use lookup_order when an order ID is "
        "given. Be concise and precise."
    ),
)

technical_agent = create_react_agent(
    model=claude_model(),
    tools=[],
    prompt=(
        "You are a technical support specialist. Troubleshoot product issues "
        "step by step, asking clarifying questions if needed. Keep "
        "instructions numbered."
    ),
)

general_agent = create_react_agent(
    model=claude_model(),
    tools=[],
    prompt="You are a friendly general customer-support agent. Help directly and concisely.",
)


def billing_node(state: GraphState) -> GraphState:
    result = billing_agent.invoke({"messages": state["messages"]})
    return {"messages": [result["messages"][-1]]}


def technical_node(state: GraphState) -> GraphState:
    result = technical_agent.invoke({"messages": state["messages"]})
    return {"messages": [result["messages"][-1]]}


def general_node(state: GraphState) -> GraphState:
    result = general_agent.invoke({"messages": state["messages"]})
    return {"messages": [result["messages"][-1]]}


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------
graph_builder = StateGraph(GraphState)
graph_builder.add_node("guardrail", guardrail_node)
graph_builder.add_node("supervisor", supervisor_node)
graph_builder.add_node("billing", billing_node)
graph_builder.add_node("technical", technical_node)
graph_builder.add_node("general", general_node)

graph_builder.add_edge(START, "guardrail")
graph_builder.add_conditional_edges(
    "guardrail", route_after_guardrail, {"supervisor": "supervisor", "end": END}
)
graph_builder.add_conditional_edges(
    "supervisor",
    route_after_supervisor,
    {"billing": "billing", "technical": "technical", "general": "general"},
)
graph_builder.add_edge("billing", END)
graph_builder.add_edge("technical", END)
graph_builder.add_edge("general", END)

app = graph_builder.compile()


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def run_query(query: str) -> None:
    print(f"\n{'=' * 70}\nUSER: {query}\n{'-' * 70}")
    result = app.invoke({"messages": [HumanMessage(content=query)], "next_agent": "", "blocked": False})
    final_message = result["messages"][-1]
    routed_to = result.get("next_agent") or "guardrail (blocked)"
    print(f"ROUTED TO: {routed_to}")
    print(f"RESPONSE: {final_message.content}")


def main() -> None:
    queries = [
        "Hi, can you check the status of order ORD-1042?",
        "My app keeps crashing whenever I open the settings page, help!",
        "Can you write me a poem about the ocean?",  # should trip the guardrail
    ]
    for q in queries:
        run_query(q)


if __name__ == "__main__":
    main()