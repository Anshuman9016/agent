"""
╔══════════════════════════════════════════════════════════════════╗
║            AI ASSISTANT — AWS Bedrock AgentCore                 ║
╠══════════════════════════════════════════════════════════════════╣
║  Framework : Microsoft AutoGen AgentChat v0.4+                  ║
║  Model     : Claude 3.5 Sonnet  (via AWS Bedrock)               ║
║  Tools     : web_search  (DuckDuckGo — real internet access)    ║
║  Runtime   : AWS Bedrock AgentCore                              ║
╚══════════════════════════════════════════════════════════════════╝

CAPABILITIES
  ✅  Says hello / greets users warmly
  ✅  Answers any question
  ✅  Searches the internet for live / recent information
  ✅  Uses Claude 3.5 Sonnet via AWS Bedrock
  ✅  Runs on AWS Bedrock AgentCore Runtime (serverless)

HOW TO RUN LOCALLY (for testing before deploying)
  python agent.py
  Then in a new terminal:
  curl -X POST http://localhost:8080/invocations \
       -H "Content-Type: application/json" \
       -d '{"prompt": "hello"}'

HOW TO DEPLOY
  See README.md — Step 4
"""

import asyncio
import logging
import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ModelInfo
from autogen_ext.models.anthropic import (
    AnthropicBedrockChatCompletionClient,
    BedrockInfo,
)
from ddgs import DDGS

# ─────────────────────────────────────────────────────────────────
# Logging  (visible in CloudWatch after deployment)
# ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
log = logging.getLogger("ai_assistant")


# ─────────────────────────────────────────────────────────────────
# TOOL: web_search
#
# AutoGen reads the function name, type hints, and docstring
# to describe this tool to Claude automatically.
# Claude will call this whenever it decides it needs fresh data.
# ─────────────────────────────────────────────────────────────────
def web_search(query: str) -> str:
    """Search the internet for up-to-date information.

    Use this tool for:
    - Current events, breaking news, recent developments
    - Live data: prices, scores, weather, stock values
    - Anything that might have changed recently
    - Verifying facts you are not confident about

    Args:
        query: A clear, specific search query string.

    Returns:
        Top search results as plain text (title, summary, URL).
    """
    log.info("🔍  Searching the web → %s", query)
    try:
        results = DDGS().text(query, max_results=5)
    except Exception as exc:
        log.warning("Search error: %s", exc)
        return f"Search failed: {exc}"

    if not results:
        return "No results found for that query."

    output = []
    for i, r in enumerate(results, 1):
        output.append(
            f"[Result {i}]\n"
            f"Title   : {r.get('title', 'N/A')}\n"
            f"Summary : {r.get('body', 'N/A')}\n"
            f"URL     : {r.get('href', 'N/A')}"
        )
    return "\n\n".join(output)


# ─────────────────────────────────────────────────────────────────
# MODEL CLIENT: Claude on AWS Bedrock
#
# Inside AgentCore Runtime, AWS credentials are automatically
# provided by the execution role — no hard-coded keys needed.
#
# Locally, credentials are picked up from:
#   1. Environment variables (AWS_ACCESS_KEY_ID etc.)
#   2. ~/.aws/credentials  (set up by `aws configure`)
# ─────────────────────────────────────────────────────────────────
def _build_model_client() -> AnthropicBedrockChatCompletionClient:
    """Create an AutoGen model client that calls Claude via Bedrock."""

    # Default to the cross-region inference profile (works for most accounts).
    # If you get an error mentioning "on-demand throughput", change this to:
    #   "anthropic.claude-3-5-sonnet-20241022-v2:0"  (us-east-1 direct)
    model_id = os.environ.get(
        "BEDROCK_MODEL_ID",
        "apac.anthropic.claude-3-5-sonnet-20240620-v1:0",
    )
    region = os.environ.get("AWS_REGION", "us-east-1")

    print("MODEL =", model_id)
    print("REGION =", region)

    return AnthropicBedrockChatCompletionClient(
        model=model_id,
        temperature=0.3,                  # slightly creative but mostly factual
        model_info=ModelInfo(
            vision=False,
            function_calling=True,        # required for tool use
            json_output=False,
            family="claude",
            structured_output=False,
        ),
        bedrock_info=BedrockInfo(
            # Empty string → SDK uses the default AWS credential chain.
            # Only fill these in if you have no ~/.aws/credentials.
            aws_access_key=os.environ.get("AWS_ACCESS_KEY_ID", ""),
            aws_secret_key=os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
            aws_session_token=os.environ.get("AWS_SESSION_TOKEN", ""),
            aws_region=region,
        ),
    )


# ─────────────────────────────────────────────────────────────────
# AUTOGEN AGENT
#
# AssistantAgent is Microsoft AutoGen's main agent class.
# It:
#   • Sends prompts to the model (Claude via Bedrock)
#   • Decides on its own when to call web_search
#   • Reads the search results and writes a final answer
#   • reflect_on_tool_use=True → after searching, Claude
#     summarises the results into a clean natural answer
# ─────────────────────────────────────────────────────────────────
def _build_agent() -> AssistantAgent:
    """Build the AutoGen AssistantAgent with Claude + web search."""
    return AssistantAgent(
        name="ai_assistant",
        model_client=_build_model_client(),
        tools=[web_search],
        reflect_on_tool_use=True,
        system_message="""You are a friendly, knowledgeable AI Assistant.

GREETING BEHAVIOUR
  When the user says hello, hi, hey, good morning, etc. — respond warmly
  and enthusiastically, then ask how you can help them today.

ANSWERING QUESTIONS
  • For general knowledge you are confident about: answer directly.
  • For anything time-sensitive — current events, news, prices, sports
    results, recent software releases, live data — ALWAYS call the
    web_search tool first. Never guess on facts that could be outdated.
  • After searching, synthesise the results into a clear, concise answer.
    Mention where the information came from when helpful.

TONE
  Be helpful, clear, and concise. Keep answers easy to understand.
  Use bullet points or numbered lists when listing multiple items.""",
    )


# ─────────────────────────────────────────────────────────────────
# AGENTCORE APP
#
# BedrockAgentCoreApp is the thin wrapper that turns any Python
# function into an AWS-hosted agent endpoint.
#
# @app.entrypoint marks the function AgentCore will call every time
# someone invokes your agent.
#
# payload = the JSON body sent by the caller
#           must contain: {"prompt": "your question here"}
# context = AgentCore metadata (session ID etc.)
# ─────────────────────────────────────────────────────────────────
app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload: dict, context=None) -> dict:
    """
    AgentCore entrypoint — called for every incoming request.

    Input  (JSON body):   {"prompt": "your question"}
    Output (JSON body):   {"response": "agent answer"}
    """
    prompt = payload.get("prompt", "").strip()

    if not prompt:
        return {
            "response": (
                "Hi! I'm your AI Assistant. "
                "Send me a message and I'll do my best to help! 😊"
            )
        }

    log.info("📨  Received prompt: %.120s", prompt)

    # Build a fresh agent per request (stateless — no memory configured).
    # This is the safest approach; add AgentCore Memory later if you want
    # the agent to remember past conversations.
    agent = _build_agent()

    # Run the AutoGen agent and collect the final text response.
    result = await agent.run(task=prompt)

    # Walk the messages from newest to oldest and return the first
    # assistant text we find.
    answer = ""
    for msg in reversed(result.messages):
        content = getattr(msg, "content", None)
        if isinstance(content, str) and content.strip():
            answer = content.strip()
            break

    if not answer:
        answer = "I wasn't able to generate a response. Please try again."

    log.info("✅  Response ready (%d chars)", len(answer))
    return {"response": answer}


# ─────────────────────────────────────────────────────────────────
# Local dev server
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("Starting local dev server on http://localhost:8080")
    app.run()
