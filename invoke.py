"""
╔══════════════════════════════════════════════════════════════════╗
║  invoke.py — Talk to your deployed AI Assistant                 ║
╠══════════════════════════════════════════════════════════════════╣
║  Run this AFTER deploying the agent with `agentcore launch`.    ║
║                                                                  ║
║  Setup:                                                          ║
║    1. Open this file in a text editor                           ║
║    2. Paste your Agent ARN into the AGENT_ARN variable below    ║
║    3. python invoke.py                                           ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import sys
import uuid
import boto3
from botocore.exceptions import ClientError

# ─────────────────────────────────────────────────────────────────
# ⚙️  CONFIGURE THESE TWO VALUES
# ─────────────────────────────────────────────────────────────────

# Paste the Agent ARN printed by `agentcore launch`
# Looks like: arn:aws:bedrock-agentcore:us-east-1:123456789012:agent-runtime/xxxxx
AGENT_ARN = "PASTE_YOUR_AGENT_ARN_HERE"

# Must match the region you deployed to
REGION = "us-east-1"

# ─────────────────────────────────────────────────────────────────


def ask_agent(prompt: str, session_id: str) -> str:
    """
    Send one message to the deployed AgentCore agent and return the answer.

    Args:
        prompt     : The question / message to send.
        session_id : A UUID string that groups turns into a session.
                     Use the same session_id across multiple calls
                     if you want the agent to treat them as one conversation.

    Returns:
        The agent's response as a plain string.
    """
    client = boto3.client("bedrock-agentcore", region_name=REGION)

    # AgentCore expects the payload as JSON-encoded bytes
    payload = json.dumps({"prompt": prompt}).encode("utf-8")

    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            runtimeSessionId=session_id,
            payload=payload,
            qualifier="DEFAULT",
        )
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        msg = exc.response["Error"]["Message"]
        return f"❌  AWS Error [{code}]: {msg}"

    # AgentCore returns a streaming body — read all chunks
    raw_chunks = []
    for chunk in response.get("response", []):
        if isinstance(chunk, bytes):
            raw_chunks.append(chunk.decode("utf-8"))
        else:
            raw_chunks.append(str(chunk))

    raw = "".join(raw_chunks)

    # Our agent returns {"response": "..."} — parse it
    try:
        data = json.loads(raw)
        return data.get("response", raw)
    except json.JSONDecodeError:
        # If parsing fails, return the raw text
        return raw


def main() -> None:
    # Guard: make sure the user has set the ARN
    if AGENT_ARN == "PASTE_YOUR_AGENT_ARN_HERE":
        print(
            "\n⚠️  You haven't set your Agent ARN yet!\n"
            "\n"
            "   1. Open invoke.py in a text editor\n"
            "   2. Find the line:  AGENT_ARN = \"PASTE_YOUR_AGENT_ARN_HERE\"\n"
            "   3. Replace it with your actual ARN from `agentcore launch`\n"
            "   4. Save the file and run again\n"
        )
        sys.exit(1)

    # One session ID for the whole interactive session
    session_id = str(uuid.uuid4())

    print("\n" + "═" * 60)
    print("  🤖  AI Assistant — powered by AutoGen + Claude on Bedrock")
    print("  🌐  Hosted on AWS Bedrock AgentCore")
    print("═" * 60)
    print("  Type your message and press Enter.")
    print("  Type  exit  or  quit  to stop.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye! 👋")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", "bye", "q"}:
            print("Agent: Goodbye! Have a great day! 👋")
            break

        print("Agent: ", end="", flush=True)
        answer = ask_agent(user_input, session_id)
        print(answer)
        print()


if __name__ == "__main__":
    main()
