import sys

import anthropic
from dotenv import load_dotenv

from agent import tools
from agent.steplog import log_step

load_dotenv()
client = anthropic.Anthropic()

MODEL = "claude-sonnet-5-5"
MAX_STEPS = 15

SYSTEM_PROMPT = """You are a network troubleshooting agent for the networkA lab: three FRR routers, r1, r2 and r3, running OSPF. You will be given a problem description. Use the tools to gather information and diagnose the problem. The tools are read-only and thus you cannot change anything on the routers.

Work one check at a time. Before each tool call, log in one sentence why you are making it. Don't make assumptions about the network state, check it with the tools.

Don't try to fix the problem. When you know the cause, stop and reply in this format:
Cause: <one sentence>
Evidence: <the tool outputs that prove it>
Suggested fix: <the change a person should make>
If you can't determine the cause, reply "Inconclusive" and summarize what you found."""

TOOL_DEFINITION = [
    {
        "name": "interfaces",
        "description": (
            "List the router's interfaces"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "router": {"type": "string", "enum": ["r1", "r2", "r3"]}
                },
            "required": ["router"],
        },
    },
    {
        "name": "ospf_neighbors",
        "description": (
            " List out the OSPF neighbors for a router."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "router": {"type": "string", "enum": ["r1", "r2", "r3"]}
                },
            "required": ["router"],
        },
    },
    {
        "name": "routes",
        "description": (
                "List the routes a router knows."
        ), 
        "input_schema": {
            "type": "object",
            "properties": {
                "router": {"type": "string", "enum": ["r1", "r2", "r3"]}
                },
            "required": ["router"],
        },   
    },
    {
        "name":"running_config",
        "description": (
            "Show the router's live configuration: its interfaces, addresses and OSPF configuration."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "router": {"type": "string", "enum": ["r1", "r2", "r3"]}
                },
            "required": ["router"],
        },
    },
    {
        "name": "ping",
        "description": (
            "Ping an IPv4 address from a router."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "router": {"type": "string", "enum": ["r1", "r2", "r3"]},
                "target": {"type": "string", "description": "An IPv4 address, e.g. 3.3.3.3"},
            },
            "required": ["router", "target"],
        },
    },
]

TOOLS = {
    "interfaces": tools.interfaces,
    "ospf_neighbors": tools.ospf_neighbors,
    "routes": tools.routes,
    "running_config": tools.running_config,
    "ping": tools.ping
}

def use_tool(tool_name, inputs):
    """Run a provided tool. Returns (output, is_error)."""
    if tool_name not in TOOLS:
        return f"Tool {tool_name} not found, allowed tools are: {list(TOOLS)}", True
    try:
        return TOOLS[tool_name](**inputs), False
    except (tools.ToolInputError, TypeError) as err:
        return str(err), True

def troubleshoot_network(problem):
    """ Troubleshoot a network problem using the defined tools and log each step. """

    # The whole conversation: the problem, the model's replies and the tool results.
    messages = [
        {"role": "user", "content": problem}
    ]

    for step in range(1, MAX_STEPS + 1): 
        response = client.messages.create(
            model = MODEL,
            max_tokens = 1024,
            system = SYSTEM_PROMPT,
            tools = TOOL_DEFINITION,
            messages = messages,
        )
        print(response)
        
        text = " ".join(b.text for b in response.content if b.type == "text")

        if response.stop_reason != "tool_use":
            log_step("report", {"step": step}, text, "")
            return text

        messages.append({"role": "assistant", "content": response.content})

        results = []
        
        for block in response.content:
            if block.type == "tool_use":
                output, is_error = use_tool(block.name, block.input)
                log_step(block.name, block.input, output, text)

                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                    "is_error": is_error                 
                })

        messages.append({"role": "user", "content": results})

    report = "Maximum number of steps reached without a diagnosis."
    log_step("report", {"step": step}, report, "")
    return report


if __name__ == "__main__":     
    print(troubleshoot_network(sys.argv[1]))
