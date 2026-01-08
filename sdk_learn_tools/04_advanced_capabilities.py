import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import (
    ImageGenTool,
    ComputerUsePreviewTool, # Preview feature
    A2ATool # Agent to Agent
)

"""
GROUP 4: ADVANCED AGENTIC CAPABILITIES
--------------------------------------
This file demonstrates autonomous action and multimodal capabilities.
"""

# ---------------------------------------------------------
# 1. IMAGE GENERATION (DALL-E)
# ---------------------------------------------------------
# Allows the agent to create images on the fly.

# Note: Requires a deployment of DALL-E 3
image_gen_tool = ImageGenTool(
    model="dall-e-3"
)


# ---------------------------------------------------------
# 2. COMPUTER USE (OS Interaction)
# ---------------------------------------------------------
# Allows the Agent to act like a user (move mouse, type keys).
# Usually returns screenshots and coordinates.

computer_use_tool = ComputerUsePreviewTool(
    display_width=1024,
    display_height=768,
    environment="windows" # or linux/mac
)


# ---------------------------------------------------------
# 3. AGENT-TO-AGENT (A2A) (Multi-Agent)
# ---------------------------------------------------------
# Allows this agent to "phone a friend" (another agent) to help with a task.

a2a_tool = A2ATool(
    project_connection_id="<CONNECTION_TO_OTHER_AGENT>"
)

print("Advanced capabilities tools initialized.")
