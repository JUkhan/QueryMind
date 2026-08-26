"""
Multi-Agent Workflow Example — OpenAI Agents SDK + Claude Sonnet 5
====================================================================

This sample builds a customer-support system with:
  - A Triage Agent that routes the conversation to the right specialist
  - A Billing Agent and a Technical Support Agent (handoff targets)
  - A shared tool (order lookup) available to the Billing Agent
  - An input guardrail that blocks off-topic requests before they're processed
  - Full conversation-turn tracing via the SDK's `Runner`

All agents run on Anthropic's Claude Sonnet 5 model (`claude-sonnet-5`),
accessed through LiteLLM as a custom model provider for the Agents SDK.

--------------------------------------------------------------------
SETUP
--------------------------------------------------------------------
1. Install dependencies:

       pip install openai-agents "litellm>=1.0" pydantic

2. Set your Anthropic API key as an environment variable:

       export ANTHROPIC_API_KEY="sk-ant-..."

3. Run:

       python multi_agent_workflow.py
--------------------------------------------------------------------
"""

import asyncio
import os

from pydantic import BaseModel

from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    RunContextWrapper,
    Runner,
    function_tool,
    input_guardrail,
)
from agents.extensions.models.litellm_model import LitellmModel

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------
# LitellmModel lets the Agents SDK (built by OpenAI) drive any LiteLLM-supported
# model. The "anthropic/" prefix tells LiteLLM to route the call to Anthropic's
# API using your ANTHROPIC_API_KEY. Swap the model id below if you want to
# point at a different Claude model string.
CLAUDE_MODEL_ID = "anthropic/claude-sonnet-5"

if not os.environ.get("ANTHROPIC_API_KEY"):
    raise RuntimeError(
        "Set the ANTHROPIC_API_KEY environment variable before running this script."
    )


def claude_model() -> LitellmModel:
    """Factory so every agent gets its own model instance bound to Claude Sonnet 5."""
    return LitellmModel(model=CLAUDE_MODEL_ID, api_key=os.environ["ANTHROPIC_API_KEY"])


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@function_tool
def lookup_order(order_id: str) -> str:
    """Look up the status of a customer order by its order ID.

    Args:
        order_id: The order identifier, e.g. "ORD-1042".
    """
    # In a real system this would hit a database or API.
    fake_orders = {
        "ORD-1042": "Shipped — arriving Aug 29, 2026.",
        "ORD-2077": "Processing — payment confirmed, not yet shipped.",
        "ORD-3090": "Delivered on Aug 20, 2026.",
    }
    return fake_orders.get(order_id, f"No order found with ID {order_id}.")


# ---------------------------------------------------------------------------
# Guardrail: keep the system on-topic (customer support only)
# ---------------------------------------------------------------------------
class TopicCheckOutput(BaseModel):
    is_off_topic: bool
    reasoning: str


guardrail_agent = Agent(
    name="Topic Guardrail Checker",
    instructions=(
        "Determine whether the user's message is a customer-support request "
        "(billing, orders, account, technical issues). If it is clearly "
        "unrelated (e.g. asking for creative writing, homework help, or "
        "general trivia), mark it as off-topic."
    ),
    output_type=TopicCheckOutput,
    model=claude_model(),
)


@input_guardrail
async def topic_guardrail(
    ctx: RunContextWrapper, agent: Agent, input_data: str
) -> GuardrailFunctionOutput:
    result = await Runner.run(guardrail_agent, input_data, context=ctx.context)
    output = result.final_output_as(TopicCheckOutput)
    return GuardrailFunctionOutput(
        output_info=output,
        tripwire_triggered=output.is_off_topic,
    )


# ---------------------------------------------------------------------------
# Specialist agents (handoff targets)
# ---------------------------------------------------------------------------
billing_agent = Agent(
    name="Billing Agent",
    handoff_description="Handles billing questions, refunds, and order status.",
    instructions=(
        "You are a billing support specialist. Help the customer with charges, "
        "refunds, invoices, and order status. Use the lookup_order tool when "
        "the customer provides an order ID. Be concise and precise."
    ),
    tools=[lookup_order],
    model=claude_model(),
)

technical_agent = Agent(
    name="Technical Support Agent",
    handoff_description="Handles technical issues, bugs, and troubleshooting.",
    instructions=(
        "You are a technical support specialist. Help the customer troubleshoot "
        "product issues step by step. Ask clarifying questions if needed, and "
        "keep instructions numbered and easy to follow."
    ),
    model=claude_model(),
)

# ---------------------------------------------------------------------------
# Triage agent — entry point that routes to the right specialist
# ---------------------------------------------------------------------------
triage_agent = Agent(
    name="Triage Agent",
    instructions=(
        "You are the first point of contact for customer support. "
        "Greet the user briefly, then route them to the correct specialist: "
        "- Billing Agent for anything about payments, refunds, or orders. "
        "- Technical Support Agent for anything about bugs or product issues. "
        "If the request doesn't clearly need a specialist, help directly."
    ),
    handoffs=[billing_agent, technical_agent],
    input_guardrails=[topic_guardrail],
    model=claude_model(),
)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
async def run_query(query: str) -> None:
    print(f"\n{'=' * 70}\nUSER: {query}\n{'-' * 70}")
    try:
        result = await Runner.run(triage_agent, query)
        print(f"FINAL AGENT: {result.last_agent.name}")
        print(f"RESPONSE: {result.final_output}")
    except InputGuardrailTripwireTriggered as e:
        print(f"BLOCKED BY GUARDRAIL: {e}")


async def main() -> None:
    queries = [
        "Hi, can you check the status of order ORD-1042?",
        "My app keeps crashing whenever I open the settings page, help!",
        "Can you write me a poem about the ocean?",  # should trip the guardrail
    ]
    for q in queries:
        await run_query(q)


if __name__ == "__main__":
    asyncio.run(main())


# Practical recommendation:

# If your workflow is basically "route to the right specialist, maybe with a tool or two," and you're already on Claude/Anthropic infra without needing LangChain's ecosystem → OpenAI Agents SDK is faster to write and reason about.
# If you need cycles, human-in-the-loop interrupts, durable/resumable execution, or a workflow that will grow into something with many conditional branches over time → LangGraph scales better, at the cost of more upfront code.