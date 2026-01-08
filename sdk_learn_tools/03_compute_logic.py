import os
import json
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import (
    FunctionTool,
    OpenApiAgentTool,
    OpenApiFunctionDefinition,
    OpenApiAnonymousAuthDetails,
    MCPTool
)

"""
GROUP 3: COMPUTE, LOGIC & INTEGRATION
-------------------------------------
This file demonstrates how to make the agent DO things (execute code, call APIs).
"""

# ---------------------------------------------------------
# 1. CODE INTERPRETER (Python Sandbox)
# ---------------------------------------------------------
# NOTE: This is often strictly defined in the Definition, not just a tool class import.
# Using standard import for demonstration.
from azure.ai.projects.models import CodeInterpreterTool

code_interpreter = CodeInterpreterTool()


# ---------------------------------------------------------
# 2. FUNCTION TOOL (Custom Code)
# ---------------------------------------------------------
# You define the schema, the Agent asks to run it, YOU run the code, and give result back.

function_tool = FunctionTool(
    name="get_weather",
    description="Gets the weather for a location",
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string"},
            "unit": {"type": "string", "enum": ["c", "f"]}
        },
        "required": ["location"]
    }
)

# ---------------------------------------------------------
# 3. OPENAPI (Swagger Imports)
# ---------------------------------------------------------
# Feed a Swagger/OpenAPI JSON spec directly to the agent.

# Assume we loaded a spec from a file
openapi_spec = { "openapi": "3.0.0", "info": {...}, "paths": {...} }

openapi_tool = OpenApiAgentTool(
    openapi=OpenApiFunctionDefinition(
        name="petstore_api",
        spec=openapi_spec,
        description="Interact with the PetStore API",
        auth=OpenApiAnonymousAuthDetails() # Or use connection auth
    )
)

# ---------------------------------------------------------
# 4. MODEL CONTEXT PROTOCOL (MCP) (Standardized Tools)
# ---------------------------------------------------------
# Connects to an MCP server that provides standard tool definitions.

mcp_tool = MCPTool(
    server_label="my-mcp-server",
    server_url="https://mcp.my-server.com",
    require_approval="always" # Safety check before running tool
)

print("Compute and Logic tools initialized.")
