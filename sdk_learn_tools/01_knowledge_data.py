import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import (
    FileSearchTool,
    MemorySearchTool,
    AzureAISearchAgentTool,
    AzureAISearchToolResource,
    AISearchIndexResource,
    AzureAISearchQueryType,
    SharepointAgentTool,
    SharepointGroundingToolParameters,
    ToolProjectConnection,
    MicrosoftFabricAgentTool,
    FabricDataAgentToolParameters
)

"""
GROUP 1: KNOWLEDGE & DATA TOOLS
--------------------------------
This file demonstrates how to give agents access to structured and unstructured data.
"""

# Establish Client
project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=os.environ["AZURE_AI_PROJECT_CONNECTION_STRING"]
)

# ---------------------------------------------------------
# 1. FILE SEARCH (Built-in RAG)
# ---------------------------------------------------------
# Uses OpenAI's vector store to search uploaded files.
# Requires: Uploading files to a vector store first.

# Create a vector store helper
with project_client.get_openai_client() as openai_client:
    vector_store = openai_client.vector_stores.create(name="learning_store")
    # (Upload logic would go here)
    
file_search_tool = FileSearchTool(vector_store_ids=[vector_store.id])


# ---------------------------------------------------------
# 2. AZURE AI SEARCH (Enterprise RAG)
# ---------------------------------------------------------
# Connects to an existing Azure AI Search index.
# Requires: A 'Connection' to your Search resource in AI Foundry.

# Retrieve the connection ID for your search service
# connection = project_client.connections.get(connection_name="my-search-service")

ai_search_tool = AzureAISearchAgentTool(
    azure_ai_search=AzureAISearchToolResource(
        indexes=[
            AISearchIndexResource(
                # Link to the Foundry Connection
                project_connection_id="<CONNECTION_ID>", 
                index_name="my-index",
                query_type=AzureAISearchQueryType.SEMANTIC
            )
        ]
    )
)

# ---------------------------------------------------------
# 3. SHAREPOINT (Enterprise Knowledge)
# ---------------------------------------------------------
# Connects to SharePoint sites/lists.
# Requires: A configured SharePoint connection in AI Foundry.

sharepoint_tool = SharepointAgentTool(
    sharepoint_grounding_preview=SharepointGroundingToolParameters(
        project_connections=[
            ToolProjectConnection(project_connection_id="<SHAREPOINT_CONNECTION_ID>")
        ]
    )
)

# ---------------------------------------------------------
# 4. MICROSOFT FABRIC (Enterprise Data)
# ---------------------------------------------------------
# Connects to OneLake / Fabric data.

fabric_tool = MicrosoftFabricAgentTool(
    fabric_dataagent_preview=FabricDataAgentToolParameters(
        project_connections=[
            ToolProjectConnection(project_connection_id="<FABRIC_CONNECTION_ID>")
        ]
    )
)

# ---------------------------------------------------------
# 5. AGENT MEMORY (Long-term Persistence)
# ---------------------------------------------------------
# Allows the agent to remember user details across sessions.
# No infra required, purely logical.

memory_tool = MemorySearchTool(
    scope="user_12345" # Isolate memory to a specific user or session
)

print("Knowledge tools initialized.")
