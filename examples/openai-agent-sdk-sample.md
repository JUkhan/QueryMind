Yes. A good way to understand this is to build a small **approval workflow** where the agent repeatedly cycles through:

**Plan → perform tool call → inspect result → continue → ask for human approval when required → resume → finish**

The OpenAI Agents SDK already has a built-in agent loop, and its HITL mechanism pauses a run by exposing `result.interruptions`; you can convert the result to a `RunState`, approve/reject the interruption, and resume the same run. ([OpenAI GitHub][1])

## Sample project

Let's build a simple **Order Processing Agent**:

```text
                    ┌─────────────────┐
                    │   User Request  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
              ┌────►│   Order Agent   │
              │     └────────┬────────┘
              │              │
              │              ▼
              │       calculate_total
              │              │
              │              ▼
              │       check_inventory
              │              │
              │              ▼
              │      Need approval?
              │         /       \
              │       No         Yes
              │       │           │
              │       │           ▼
              │       │     ┌───────────┐
              │       │     │   HUMAN   │
              │       │     │  APPROVAL │
              │       │     └─────┬─────┘
              │       │           │
              │       │      approve/reject
              │       │           │
              │       └───────────┘
              │                   │
              │                   ▼
              │            execute_order
              │                   │
              └───────────────────┘
                              │
                              ▼
                         Final result
```

The important part is that **the cycle is not something you manually implement as a `while` loop around the LLM**. The Agents SDK's `Runner` manages the agent/tool loop for you. ([OpenAI GitHub][1])

### 1. Install

```bash
uv init openai-agent-hitl-demo
cd openai-agent-hitl-demo

uv add openai-agents
```

Set your API key:

```bash
export OPENAI_API_KEY="your-api-key"
```

On Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="your-api-key"
```

---

## 2. Complete example

Create `main.py`:

```python
import asyncio
from typing import Any

from agents import Agent, Runner, function_tool


# ============================================================
# Tools
# ============================================================

@function_tool
def calculate_order_total(
    product: str,
    quantity: int,
    unit_price: float,
) -> str:
    """Calculate the total price of an order."""

    total = quantity * unit_price

    return (
        f"Product: {product}\n"
        f"Quantity: {quantity}\n"
        f"Unit price: ${unit_price:.2f}\n"
        f"Total: ${total:.2f}"
    )


@function_tool
def check_inventory(
    product: str,
    quantity: int,
) -> str:
    """Check whether enough inventory exists."""

    # Fake inventory for demonstration.
    inventory = {
        "laptop": 10,
        "monitor": 20,
        "keyboard": 50,
    }

    available = inventory.get(product.lower(), 0)

    if available >= quantity:
        return (
            f"Inventory available.\n"
            f"Product: {product}\n"
            f"Requested: {quantity}\n"
            f"Available: {available}"
        )

    return (
        f"INSUFFICIENT INVENTORY.\n"
        f"Product: {product}\n"
        f"Requested: {quantity}\n"
        f"Available: {available}"
    )


@function_tool(needs_approval=True)
def execute_order(
    product: str,
    quantity: int,
    total_price: float,
) -> str:
    """
    Execute the order.

    This operation requires human approval.
    """

    # In a real application this would call:
    #
    #   payment API
    #   order management system
    #   database
    #   ERP
    #
    # But for this example we simply return a message.

    return (
        f"ORDER EXECUTED SUCCESSFULLY.\n"
        f"Product: {product}\n"
        f"Quantity: {quantity}\n"
        f"Total charged: ${total_price:.2f}"
    )


# ============================================================
# Agent
# ============================================================

order_agent = Agent(
    name="Order Processing Agent",

    instructions="""
You are an order processing agent.

Your job is to process customer orders safely.

Follow this workflow:

1. Understand the customer's order.
2. Calculate the order total.
3. Check inventory.
4. If inventory is insufficient, explain the problem and stop.
5. If inventory is sufficient, execute the order.
6. The execute_order tool requires human approval.
7. NEVER attempt to bypass the approval requirement.
8. After the order has been executed, provide a concise summary.

Always use the tools rather than pretending that an operation happened.
""",

    tools=[
        calculate_order_total,
        check_inventory,
        execute_order,
    ],
)


# ============================================================
# Human approval
# ============================================================

async def ask_human_approval(interruption: Any) -> bool:
    """
    Ask a human whether the pending tool call should be approved.
    """

    print("\n" + "=" * 60)
    print(" HUMAN-IN-THE-LOOP INTERRUPTION")
    print("=" * 60)

    print(f"\nAgent: {interruption.agent.name}")
    print(f"Tool:  {interruption.name}")

    print("\nArguments:")
    print(interruption.arguments)

    print("\nThis operation requires human approval.")

    while True:
        answer = input("\nApprove this operation? [y/n]: ").strip().lower()

        if answer in ("y", "yes"):
            return True

        if answer in ("n", "no"):
            return False

        print("Please enter y or n.")


# ============================================================
# Main workflow
# ============================================================

async def main():

    print("=" * 60)
    print(" ORDER PROCESSING AGENT")
    print("=" * 60)

    user_request = """
    I want to buy 2 laptops.
    Each laptop costs $1500.
    """

    print("\nUSER:")
    print(user_request)

    # --------------------------------------------------------
    # Initial agent execution
    # --------------------------------------------------------

    result = await Runner.run(
        order_agent,
        user_request,
        max_turns=10,
    )

    # --------------------------------------------------------
    # HITL / interruption cycle
    # --------------------------------------------------------

    while result.interruptions:

        print("\nAgent execution paused.")

        # Convert the paused result into resumable state.
        state = result.to_state()

        # ----------------------------------------------------
        # Process every pending interruption
        # ----------------------------------------------------

        for interruption in result.interruptions:

            approved = await ask_human_approval(interruption)

            if approved:

                print("\nHuman decision: APPROVED")

                state.approve(
                    interruption,
                    always_approve=False,
                )

            else:

                print("\nHuman decision: REJECTED")

                state.reject(
                    interruption,
                    rejection_message=(
                        "The human reviewer rejected this order."
                    ),
                )

        # ----------------------------------------------------
        # Resume the SAME agent run
        # ----------------------------------------------------

        result = await Runner.run(
            order_agent,
            state,
            max_turns=10,
        )

    # --------------------------------------------------------
    # Final output
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print(" FINAL RESULT")
    print("=" * 60)

    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
```

The key API here is `needs_approval=True`. When the model requests that tool, the SDK pauses rather than executing it and exposes the pending tool call through `result.interruptions`. You then use `state.approve()` or `state.reject()` and call `Runner.run()` again with the `RunState`. ([OpenAI GitHub][2])

## 3. What happens at runtime

You should see something conceptually like:

```text
============================================================
 ORDER PROCESSING AGENT
============================================================

USER:

I want to buy 2 laptops.
Each laptop costs $1500.


Agent execution paused.

============================================================
 HUMAN-IN-THE-LOOP INTERRUPTION
============================================================

Agent: Order Processing Agent
Tool:  execute_order

Arguments:
{
    "product": "laptop",
    "quantity": 2,
    "total_price": 3000
}

This operation requires human approval.

Approve this operation? [y/n]:
```

You type:

```text
y
```

Then:

```text
Human decision: APPROVED
```

The agent resumes.

```text
============================================================
 FINAL RESULT
============================================================

ORDER EXECUTED SUCCESSFULLY.

Product: laptop
Quantity: 2
Total charged: $3000.00
```

---

# Where is the cycle?

The interesting part is this:

```python
result = await Runner.run(
    order_agent,
    user_request,
    max_turns=10,
)
```

The SDK internally performs a loop similar to:

```text
LLM
 │
 ├── final answer ──────────────► DONE
 │
 ├── tool call
 │      │
 │      ▼
 │   execute tool
 │      │
 │      └──────────────────────► LLM
 │
 └── handoff
        │
        └──────────────────────► another agent
```

The SDK documentation describes this as the agent loop: call the LLM, execute tool calls, handle handoffs, and continue until a final output is produced or the turn limit is reached. ([OpenAI GitHub][1])

With HITL, we add another branch:

```text
                         ┌───────────────┐
                         │      LLM      │
                         └───────┬───────┘
                                 │
                         decides tool call
                                 │
                                 ▼
                       ┌───────────────────┐
                       │ needs_approval ?  │
                       └─────────┬─────────┘
                           ┌─────┴─────┐
                          NO           YES
                           │            │
                           ▼            ▼
                     execute tool   INTERRUPT
                           │            │
                           │            ▼
                           │       HUMAN REVIEW
                           │         /      \
                           │       YES       NO
                           │        │         │
                           │        ▼         ▼
                           │     approve    reject
                           │        │         │
                           └────────┴─────────┘
                                    │
                                    ▼
                                   LLM
```

This is the important architectural concept.

---

# 4. Why `RunState` is important

This:

```python
state = result.to_state()
```

captures the paused execution state.

Then:

```python
state.approve(interruption)
```

records the human decision.

And:

```python
result = await Runner.run(
    order_agent,
    state,
)
```

continues the **same execution**.

So you don't need to restart the conversation from scratch.

The SDK specifically supports serializing paused state, which is important for real applications where the approval may happen minutes or hours later. ([OpenAI GitHub][2])

---

# 5. Real-world architecture

For your automation-pipeline idea, I'd evolve this example into:

```text
                       ┌──────────────────┐
                       │      FastAPI     │
                       └────────┬─────────┘
                                │
                         Start workflow
                                │
                                ▼
                       ┌──────────────────┐
                       │   Agents Runner  │
                       └────────┬─────────┘
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
                 ▼                             ▼
          Agent reasoning                Tool execution
                 │                             │
                 │                             ▼
                 │                      needs approval?
                 │                             │
                 │                             ▼
                 │                     ┌───────────────┐
                 │                     │     PAUSED    │
                 │                     └───────┬───────┘
                 │                             │
                 │                     persist RunState
                 │                             │
                 │                             ▼
                 │                     ┌───────────────┐
                 │                     │   PostgreSQL  │
                 │                     └───────────────┘
                 │
                 │
                 │       Human approval
                 │              │
                 │              ▼
                 │       ┌───────────────┐
                 │       │ Approval API  │
                 │       └───────┬───────┘
                 │               │
                 └───────────────┘
                                 │
                                 ▼
                         Resume RunState
                                 │
                                 ▼
                         Agent continues
```

For example:

```text
POST /workflows
```

starts the workflow.

If approval is required:

```text
GET /approvals/{approval_id}
```

returns:

```json
{
  "status": "pending",
  "tool": "execute_order",
  "arguments": {
    "product": "laptop",
    "quantity": 2,
    "total_price": 3000
  }
}
```

Then:

```text
POST /approvals/{approval_id}/approve
```

or:

```text
POST /approvals/{approval_id}/reject
```

The backend loads the persisted `RunState` and resumes the agent.

That gives you a proper **long-running agent workflow**, rather than a CLI demo.

---

## 6. One important distinction

There are actually **three different mechanisms** worth keeping separate:

| Mechanism          | Purpose                                    |
| ------------------ | ------------------------------------------ |
| Agent loop / cycle | Continue reasoning and tool execution      |
| HITL interruption  | Stop and wait for a human                  |
| Guardrail tripwire | Stop because a safety/business rule failed |

For example:

```text
                    Agent
                      │
                      ▼
                 Tool request
                      │
          ┌───────────┼───────────┐
          │           │           │
          ▼           ▼           ▼
       Normal       HITL       Guardrail
       tool call   approval     check
          │           │           │
          ▼           ▼           ▼
       execute      PAUSE       STOP
                    │
                    ▼
                  HUMAN
                    │
               approve/reject
                    │
                    ▼
                 RESUME
```

The SDK also provides guardrails and tripwires specifically for stopping execution when validation fails. ([OpenAI GitHub][3])

### The next step I'd recommend

For the kind of **automation pipeline + message broker + FastAPI/PostgreSQL** architecture you've been exploring, the more useful sample would be a **production-style mini workflow**:

```text
Event
  ↓
Message Broker
  ↓
FastAPI Worker
  ↓
OpenAI Agent
  ↓
┌──────────────────────────────┐
│ Agent Cycle                  │
│                              │
│ analyze → tool → evaluate    │
│    ↑                 │       │
│    └─────────────────┘       │
└──────────────────────────────┘
              ↓
       High-risk action?
          /         \
        NO           YES
        ↓             ↓
    continue      HITL Interrupt
                      ↓
                PostgreSQL
                      ↓
                Approval UI
                      ↓
              approve / reject
                      ↓
                 ResumeState
                      ↓
                 Agent Cycle
                      ↓
                   DONE
```

That would demonstrate **Agents SDK + cycles + HITL + FastAPI + PostgreSQL + message broker + persistent/resumable state**, which is much closer to a real automation platform.

[1]: https://openai.github.io/openai-agents-python/running_agents/?utm_source=chatgpt.com "Running agents - OpenAI Agents SDK"
[2]: https://openai.github.io/openai-agents-python/human_in_the_loop/?utm_source=chatgpt.com "Human-in-the-loop - OpenAI Agents SDK"
[3]: https://openai.github.io/openai-agents-python/guardrails/?utm_source=chatgpt.com "Guardrails - OpenAI Agents SDK"
