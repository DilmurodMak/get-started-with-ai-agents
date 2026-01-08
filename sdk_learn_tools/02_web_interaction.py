import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import (
    WebSearchTool, # Or WebSearchPreviewTool depending on version
    BingGroundingAgentTool,
    BingGroundingSearchToolParameters,
    BingGroundingSearchConfiguration,
    BingCustomSearchAgentTool,
    BingCustomSearchToolParameters,
    BingCustomSearchConfiguration,
    BrowserAutomationAgentTool,
    BrowserAutomationToolParameters,
    BrowserAutomationToolConnectionParameters,
    ApproximateLocation
)

"""
GROUP 2: WEB & EXTERNAL INTERACTION
-----------------------------------
This file demonstrates how to give agents access to the live internet.
"""

project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=os.environ["AZURE_AI_PROJECT_CONNECTION_STRING"]
)

# ---------------------------------------------------------
# 1. WEB SEARCH (General)
# ---------------------------------------------------------
# Performs standard Google/Bing style searches for public info.

web_search_tool = WebSearchTool(
    user_location=ApproximateLocation(country="US", city="Seattle")
)

# ---------------------------------------------------------
# 2. BING GROUNDING (Fact Checking)
# ---------------------------------------------------------
# Specifically designed to ground LLM responses in real facts.

bing_grounding_tool = BingGroundingAgentTool(
    bing_grounding=BingGroundingSearchToolParameters(
        search_configurations=[
            BingGroundingSearchConfiguration(
                project_connection_id="<BING_CONNECTION_ID>"
            )
        ]
    )
)

# ---------------------------------------------------------
# 3. BING CUSTOM SEARCH (Domain Specific)
# ---------------------------------------------------------
# Searches only a specific subset of the web you defined in Bing Custom Search portal.

bing_custom_tool = BingCustomSearchAgentTool(
    bing_custom_search_preview=BingCustomSearchToolParameters(
        search_configurations=[
            BingCustomSearchConfiguration(
                project_connection_id="<BING_CUSTOM_CONNECTION_ID>",
                instance_name="my-custom-search-instance"
            )
        ]
    )
)

# ---------------------------------------------------------
# 4. BROWSER AUTOMATION (Headless Interaction)
# ---------------------------------------------------------
# Allows the agent to open a browser, click, and read pages dynamically.

browser_tool = BrowserAutomationAgentTool(
    browser_automation_preview=BrowserAutomationToolParameters(
        connection=BrowserAutomationToolConnectionParameters(
            project_connection_id="<BROWSER_SERVICE_CONNECTION_ID>"
        )
    )
)

print("Web tools initialized.")
