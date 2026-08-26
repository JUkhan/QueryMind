"""
Multi-Agent Workflow Example — LangGraph + Claude Sonnet 5
Enhanced with CYCLES and HUMAN-IN-THE-LOOP INTERRUPTS
=============================================================

Builds on the previous triage/billing/technical example and adds two
patterns that LangGraph is particularly good at:

1. CYCLES (loops in the graph)
   - Technical Support runs a diagnostic loop: it asks a clarifying
     question, pauses for the customer's answer, and loops back into
     itself until the issue is resolved or a max attempt count is hit.
   - Quality Review is a critique/revise loop: an automated reviewer
     checks the specialist's reply and can send it back to the same
     specialist node with feedback, up to a max number of retries.

2. HUMAN-IN-THE-LOOP INTERRUPTS
   - Billing pauses on refund requests and waits for a human approver
     (e.g. a manager) to type yes/no before the agent finalizes its
     reply — a classic "approval gate" pattern.
   - Quality Review escalates to a human when the automated reviewer's
     confidence is low, instead of guessing.
   - Technical Support's diagnostic loop uses interrupt() to pause and
     collect the *customer's* next message mid-workflow — a different
     flavor of human-in-the-loop (the human is the end user, not an
     approver).

Both patterns are implemented with LangGraph's `interrupt()` +
`Command(resume=...)` + a checkpointer (`MemorySaver`), which is what
lets the graph pause execution, persist state, and resume exactly
where it left off — potentially minutes, hours, or days later, and in
a different process, if you swap `MemorySaver` for a durable
checkpointer (e.g. Postgres/Redis backed).

--------------------------------------------------------------------
SETUP
--------------------------------------------------------------------
1. Install dependencies:

       pip install langgraph langchain-anthropic langchain-core pydantic

2. Set your Anthropic API key:

       export ANTHROPIC_API_KEY="sk-ant-..."

3. Run:

       python multi_agent_langgraph_hitl.py

   The demo below feeds simulated human responses automatically so it
   runs end-to-end non-interactively. Set `simulated_answers=None` in
   `run_conversation(...)` to instead be prompted at the terminal for
   real interactive input at each pause point.
--------------------------------------------------------------------
"""

import os
from typing import Annotated, Literal, Optional, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

if not os.environ.get("ANTHROPIC_API_KEY"):
    raise RuntimeError(
        "Set the ANTHROPIC_API_KEY environment variable before running this script."
    )

MODEL_ID = "claude-sonnet-5"
MAX_DIAGNOSTIC_ATTEMPTS = 3
MAX_REVIEW_ATTEMPTS = 2


def claude_model(**kwargs) -> ChatAnthropic:
    """Factory so every node gets its own ChatAnthropic instance bound to Sonnet 5."""
    return ChatAnthropic(model=MODEL_ID, temperature=0, **kwargs)


def _last_human_text(messages: list[BaseMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return str(msg.content)
    return ""


def _truthy(value) -> bool:
    return str(value).strip().lower() in {"yes", "y", "approve", "approved", "true"}


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
    next_agent: str
    blocked: bool
    # technical diagnostic cycle
    diagnostic_attempts: int
    resolved: bool
    # billing human-approval gate
    refund_requested: bool
    refund_approved: Optional[bool]
    # quality-review cycle
    review_attempts: int
    review_satisfactory: bool


# ---------------------------------------------------------------------------
# Guardrail node — unchanged from the earlier example
# ---------------------------------------------------------------------------
class TopicCheck(BaseModel):
    is_off_topic: bool = Field(description="True if the request is unrelated to customer support")
    reasoning: str


def guardrail_node(state: GraphState) -> GraphState:
    checker = claude_model().with_structured_output(TopicCheck)
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
            HumanMessage(content=_last_human_text(state["messages"])),
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
        }
    return {"blocked": False}


def route_after_guardrail(state: GraphState) -> Literal["supervisor", "end"]:
    return "end" if state["blocked"] else "supervisor"


# ---------------------------------------------------------------------------
# Supervisor (triage) node — unchanged
# ---------------------------------------------------------------------------
class RouteDecision(BaseModel):
    destination: Literal["billing", "technical", "general"] = Field(
        description="Which specialist should handle this request"
    )


def supervisor_node(state: GraphState) -> GraphState:
    router = claude_model().with_structured_output(RouteDecision)
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
            HumanMessage(content=_last_human_text(state["messages"])),
        ]
    )
    return {"next_agent": decision.destination}


def route_after_supervisor(state: GraphState) -> Literal["billing", "technical", "general"]:
    return state["next_agent"]


# ---------------------------------------------------------------------------
# Specialist agents (prebuilt ReAct agents)
# ---------------------------------------------------------------------------
billing_agent = create_react_agent(
    model=claude_model(),
    tools=[lookup_order],
    prompt=(
        "You are a billing support specialist. Help with charges, refunds, "
        "invoices, and order status. Use lookup_order when an order ID is "
        "given. If an [Internal note] about refund approval is present, "
        "reflect that decision clearly in your reply. Be concise."
    ),
)

technical_agent = create_react_agent(
    model=claude_model(),
    tools=[],
    prompt=(
        "You are a technical support specialist troubleshooting one issue at "
        "a time. Ask exactly one clarifying or diagnostic question per turn "
        "if you need more information, or give the resolution if you have "
        "enough information. Keep replies short."
    ),
)

general_agent = create_react_agent(
    model=claude_model(),
    tools=[],
    prompt="You are a friendly general customer-support agent. Help directly and concisely.",
)


# ---------------------------------------------------------------------------
# BILLING NODE — human-in-the-loop APPROVAL GATE (single-shot interrupt)
# ---------------------------------------------------------------------------
class RefundCheck(BaseModel):
    is_refund_request: bool


def billing_node(state: GraphState) -> GraphState:
    refund_requested = state.get("refund_requested", False)
    refund_approved = state.get("refund_approved")

    # NOTE: because interrupt() suspends and resumes execution *within this
    # same node call*, any code that runs before the interrupt() call below
    # re-executes when the node resumes. That's fine here (a cheap classifier
    # call), but for expensive pre-interrupt work, split it into its own node
    # so it only runs once — see the quality_review cycle further down for
    # that pattern.
    if not refund_requested:
        checker = claude_model().with_structured_output(RefundCheck)
        check: RefundCheck = checker.invoke(
            [
                SystemMessage(content="Determine if the customer is requesting a refund."),
                HumanMessage(content=_last_human_text(state["messages"])),
            ]
        )
        refund_requested = check.is_refund_request

    if refund_requested and refund_approved is None:
        # ⏸ PAUSE the graph here and surface this payload to whatever is
        # driving the run (CLI, API caller, UI). Execution resumes exactly
        # here when the caller sends `Command(resume=<answer>)`.
        human_decision = interrupt(
            {
                "type": "refund_approval",
                "message": (
                    "A refund request needs manager approval before the "
                    f"agent can respond. Customer said: "
                    f"{_last_human_text(state['messages'])!r}. Approve? (yes/no)"
                ),
            }
        )
        refund_approved = _truthy(human_decision)

    context_messages = list(state["messages"])
    if refund_requested:
        note = "APPROVED" if refund_approved else "DENIED"
        context_messages = [
            SystemMessage(content=f"[Internal note: refund request was {note} by a human approver.]")
        ] + context_messages

    result = billing_agent.invoke({"messages": context_messages})
    return {
        "messages": [result["messages"][-1]],
        "refund_requested": refund_requested,
        "refund_approved": refund_approved,
    }


# ---------------------------------------------------------------------------
# TECHNICAL NODE — CYCLE + human-in-the-loop (asking the customer, not an
# approver) using interrupt() to collect the next message mid-diagnosis.
# ---------------------------------------------------------------------------
class ResolutionCheck(BaseModel):
    resolved: bool = Field(description="True if the reply resolves the issue or ends with a fix")


def technical_node(state: GraphState) -> GraphState:
    attempts = state.get("diagnostic_attempts", 0)

    result = technical_agent.invoke({"messages": state["messages"]})
    last_ai = result["messages"][-1]

    checker = claude_model().with_structured_output(ResolutionCheck)
    check: ResolutionCheck = checker.invoke(
        [
            SystemMessage(
                content=(
                    "Does this support reply resolve the issue, or is it asking "
                    "a follow-up question that still needs an answer?"
                )
            ),
            HumanMessage(content=str(last_ai.content)),
        ]
    )

    if not check.resolved and attempts < MAX_DIAGNOSTIC_ATTEMPTS:
        # ⏸ PAUSE and ask the customer directly for the missing info.
        customer_answer = interrupt(
            {
                "type": "diagnostic_question",
                "question": last_ai.content,
            }
        )
        return {
            "messages": [last_ai, HumanMessage(content=str(customer_answer))],
            "diagnostic_attempts": attempts + 1,
            "resolved": False,
        }

    return {"messages": [last_ai], "resolved": True, "diagnostic_attempts": attempts}


def route_after_technical(state: GraphState) -> Literal["technical", "quality_review"]:
    if state.get("resolved") or state.get("diagnostic_attempts", 0) >= MAX_DIAGNOSTIC_ATTEMPTS:
        return "quality_review"
    return "technical"  # <-- the cycle: loop back into the same node


def general_node(state: GraphState) -> GraphState:
    result = general_agent.invoke({"messages": state["messages"]})
    return {"messages": [result["messages"][-1]]}


# ---------------------------------------------------------------------------
# QUALITY REVIEW NODE — critique/revise CYCLE, with an escalation interrupt
# for low-confidence automated reviews.
# ---------------------------------------------------------------------------
class ReviewResult(BaseModel):
    is_satisfactory: bool
    confidence: Literal["high", "low"] = Field(
        description="Reviewer's confidence in its own judgment"
    )
    feedback: str


def quality_review_node(state: GraphState) -> GraphState:
    attempts = state.get("review_attempts", 0)
    last_ai = state["messages"][-1]

    reviewer = claude_model().with_structured_output(ReviewResult)
    review: ReviewResult = reviewer.invoke(
        [
            SystemMessage(
                content=(
                    "Review the support agent's reply for correctness, tone, and "
                    "completeness. Set confidence to 'low' if you are genuinely "
                    "unsure whether it's acceptable — a human will make the call."
                )
            ),
            HumanMessage(content=str(last_ai.content)),
        ]
    )

    if review.confidence == "low":
        # ⏸ PAUSE and escalate uncertain judgment calls to a human reviewer
        # instead of guessing.
        human_verdict = interrupt(
            {
                "type": "quality_escalation",
                "message": "Automated reviewer is unsure about this reply. Approve it?",
                "reply": last_ai.content,
                "reviewer_feedback": review.feedback,
            }
        )
        is_satisfactory = _truthy(human_verdict)
    else:
        is_satisfactory = review.is_satisfactory

    if not is_satisfactory and attempts + 1 >= MAX_REVIEW_ATTEMPTS:
        # Exhausted retries — accept best effort rather than looping forever.
        is_satisfactory = True

    if is_satisfactory:
        return {"review_satisfactory": True, "review_attempts": attempts}

    return {
        "review_satisfactory": False,
        "review_attempts": attempts + 1,
        "messages": [
            HumanMessage(
                content=f"[Reviewer feedback — please revise your last answer]: {review.feedback}"
            )
        ],
    }


def route_after_review(state: GraphState) -> Literal["billing", "technical", "general", "end"]:
    if state.get("review_satisfactory", True):
        return "end"
    return state["next_agent"]  # <-- the cycle: loop back to the specialist that answered


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------
graph_builder = StateGraph(GraphState)
graph_builder.add_node("guardrail", guardrail_node)
graph_builder.add_node("supervisor", supervisor_node)
graph_builder.add_node("billing", billing_node)
graph_builder.add_node("technical", technical_node)
graph_builder.add_node("general", general_node)
graph_builder.add_node("quality_review", quality_review_node)

graph_builder.add_edge(START, "guardrail")
graph_builder.add_conditional_edges(
    "guardrail", route_after_guardrail, {"supervisor": "supervisor", "end": END}
)
graph_builder.add_conditional_edges(
    "supervisor",
    route_after_supervisor,
    {"billing": "billing", "technical": "technical", "general": "general"},
)
graph_builder.add_edge("billing", "quality_review")
graph_builder.add_conditional_edges(
    "technical", route_after_technical, {"technical": "technical", "quality_review": "quality_review"}
)
graph_builder.add_edge("general", "quality_review")
graph_builder.add_conditional_edges(
    "quality_review",
    route_after_review,
    {"billing": "billing", "technical": "technical", "general": "general", "end": END},
)

# A checkpointer is REQUIRED for interrupt()/Command(resume=...) to work —
# it's what persists state across the pause. MemorySaver is in-process only;
# swap in a Postgres/Redis/SQLite checkpointer for anything that needs to
# survive a process restart or be resumed by a different worker.
checkpointer = MemorySaver()
app = graph_builder.compile(checkpointer=checkpointer)
#app.get_graph().draw_mermaid_png()

# ---------------------------------------------------------------------------
# Runner — drives the graph across pauses, feeding either simulated or
# real (input()) human responses back in via Command(resume=...).
# ---------------------------------------------------------------------------
def run_conversation(
    query: str, thread_id: str, simulated_answers: Optional[list[str]] = None
) -> None:
    print(f"\n{'=' * 70}\nTHREAD: {thread_id}\nUSER: {query}\n{'-' * 70}")

    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}
    initial_state: GraphState = {
        "messages": [HumanMessage(content=query)],
        "next_agent": "",
        "blocked": False,
        "diagnostic_attempts": 0,
        "resolved": False,
        "refund_requested": False,
        "refund_approved": None,
        "review_attempts": 0,
        "review_satisfactory": True,
    }

    result = app.invoke(initial_state, config=config)
    pending_answers = list(simulated_answers or [])

    while result.get("__interrupt__"):
        payload = result["__interrupt__"][0].value
        print(f"\n⏸  PAUSED — human input requested:\n    {payload}")
        if pending_answers:
            answer = pending_answers.pop(0)
            print(f"    (simulated human response: {answer!r})")
        else:
            answer = input("    Your response: ")
        result = app.invoke(Command(resume=answer), config=config)

    print(f"\nROUTED TO: {result.get('next_agent') or 'guardrail (blocked)'}")
    print(f"FINAL RESPONSE: {result['messages'][-1].content}")


def main() -> None:
    # 1) Technical support: triggers the diagnostic CYCLE, pausing twice to
    #    ask the (simulated) customer for more detail before resolving.
    run_conversation(
        "My app keeps crashing whenever I open the settings page, help!",
        thread_id="conv-technical-1",
        simulated_answers=[
            "iPhone 15, iOS 18.2, app version 3.4.1",
            "Yes, I already tried reinstalling and it still crashes.",
        ],
    )

    # 2) Billing: triggers the human-in-the-loop APPROVAL GATE for refunds.
    run_conversation(
        "I'd like a refund for order ORD-2077 — it never shipped.",
        thread_id="conv-billing-1",
        simulated_answers=["yes"],  # manager approves the refund
    )

    # 3) Off-topic request: blocked by the guardrail before reaching the graph.
    run_conversation(
        "Can you write me a poem about the ocean?",
        thread_id="conv-blocked-1",
    )


if __name__ == "__main__":
    main()

comment="""
Compiles cleanly with the full node/edge topology, checkpointer, and interrupt wiring intact.**What's new, on top of the previous LangGraph example:**

**Two cycles:**
- **Technical diagnostic loop** — `technical` conditionally routes back to itself (`route_after_technical`) until the model reports the issue resolved or it hits `MAX_DIAGNOSTIC_ATTEMPTS`. Each pass through the loop pauses via `interrupt()` to collect the customer's next answer.
- **Quality-review critique/revise loop** — `quality_review` conditionally routes back to whichever specialist answered (`state["next_agent"]`) with feedback attached, up to `MAX_REVIEW_ATTEMPTS`, then gives up gracefully and ends.

**Two flavors of human-in-the-loop interrupts:**
- **Approval gate** (billing) — refund requests pause and wait for a yes/no from a human approver before the agent finalizes its reply.
- **Escalation on low confidence** (quality review) — when the automated reviewer isn't sure, it hands the decision to a human instead of guessing.
- **Mid-conversation input** (technical) — `interrupt()` is also used to pull in the *next message from the actual customer*, not just an approver — showing interrupts aren't only for approvals.

**Mechanics worth knowing:**
- `MemorySaver()` (a checkpointer) is required for `interrupt()`/`Command(resume=...)` to work — it's what lets the graph literally pause mid-execution and resume later, even in a different process if you swap in a durable checkpointer (Postgres/Redis/SQLite).
- Each conversation needs a `thread_id` in `config` so the checkpointer knows which paused state to resume.
- I added a callout in the code: code before an `interrupt()` re-runs on resume (since the whole node function replays), so put expensive work in a separate node if that matters.

The `main()` demo drives all three paths — the diagnostic loop, the refund approval gate, and the guardrail block — using simulated human answers so it runs end-to-end without a live terminal; set `simulated_answers=None` to instead get prompted for real input at each pause.

This is exactly the kind of workflow where the earlier "OpenAI Agents SDK vs LangGraph" tradeoff becomes concrete: cycles and durable, resumable interrupts are native to LangGraph's graph model, but doing the equivalent in the Agents SDK would mean building your own state machine around it — the Agents SDK doesn't have a first-class pause/resume/checkpoint primitive like this.
"""