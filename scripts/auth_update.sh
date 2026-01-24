#!/bin/bash

# This script automates the assignment of roles to the Azure AI Agent's identity.
# It targets the LATEST (most recently created) Agent Identity, assuming this corresponds to the currently "Published" agent.

# --- CONFIGURATION: Define Roles to Assign here ---
# Format: "Role Name"
ROLES=(
    "Storage Blob Data Contributor"
    "Search Index Data Reader"
    "Search Index Data Contributor"
    "Search Service Contributor"
)
# --------------------------------------------------

# Ensure required environment variables are set
if [ -z "$AZURE_RESOURCE_GROUP" ]; then
    echo "Error: AZURE_RESOURCE_GROUP is not set."
    exit 1
fi

AGENT_NAME="${AZURE_AI_AGENT_NAME:-agent-template-assistant}"
echo "Updating permissions for Agent in Resource Group: $AZURE_RESOURCE_GROUP"

# 1. Identify the Target Agent Identity
AGENT_PRINCIPAL_ID=""
IDENTITY_NAME=""

# Strategy: Construct the Project Agent Identity Name
if [ -n "$AZURE_EXISTING_AIPROJECT_RESOURCE_ID" ]; then
    ACCOUNT_NAME=$(echo "$AZURE_EXISTING_AIPROJECT_RESOURCE_ID" | sed -n 's/.*accounts\/\([^\/]*\).*/\1/p')
    PROJECT_NAME=$(echo "$AZURE_EXISTING_AIPROJECT_RESOURCE_ID" | sed -n 's/.*projects\/\([^\/]*\).*/\1/p')
    
    if [ -n "$ACCOUNT_NAME" ] && [ -n "$PROJECT_NAME" ]; then
        IDENTITY_NAME="${ACCOUNT_NAME}-${PROJECT_NAME}-AgentIdentity"
    fi
fi

if [ -n "$IDENTITY_NAME" ]; then
    echo "Looking for all identities with name: $IDENTITY_NAME"
    
    # Query for IDs and Creation Dates, sort by Date DESC.
    # We will loop through ALL of them to ensure multiple agents (e.g. V5 and V2) are covered.
    
    ALL_AGENTS_JSON=$(az ad sp list \
        --display-name "$IDENTITY_NAME" \
        --query "sort_by([], &createdDateTime)" \
        --output json)
        
    if [ "$ALL_AGENTS_JSON" != "null" ] && [ -n "$ALL_AGENTS_JSON" ] && [ "$ALL_AGENTS_JSON" != "[]" ]; then
         # Extract all IDs into a space-separated string
         AGENT_PRINCIPAL_IDS=$(echo "$ALL_AGENTS_JSON" | jq -r '.[].id')
         
         # Optional: Check if we want to filter only "recent" ones if we have too many?
         # For now, applying to all matching the Project Identity pattern is the safest "fix-all" approach.
         echo "Found the following Agent Identities:"
         echo "$ALL_AGENTS_JSON" | jq -r '.[] | "  - ID: \(.id) | Created: \(.createdDateTime) | Name: \(.displayName)"'
    else
        echo "Warning: No identities found matching pattern $IDENTITY_NAME"
    fi
fi

# Fallback: finding by simple Agent Name if logic above failed
if [ -z "$AGENT_PRINCIPAL_IDS" ]; then
    echo "Fallback: Looking for identities with name: $AGENT_NAME"
     LATEST_AGENT_JSON=$(az ad sp list \
        --display-name "$AGENT_NAME" \
        --query "sort_by([], &createdDateTime)" \
        --output json)
        
     if [ "$LATEST_AGENT_JSON" != "null" ] && [ -n "$LATEST_AGENT_JSON" ] && [ "$LATEST_AGENT_JSON" != "[]" ]; then
         AGENT_PRINCIPAL_IDS=$(echo "$LATEST_AGENT_JSON" | jq -r '.[].id')
         echo "Found Agent Identities (Fallback):"
         echo "$LATEST_AGENT_JSON" | jq -r '.[] | "  - ID: \(.id) | Created: \(.createdDateTime)"'
     fi
fi

if [ -z "$AGENT_PRINCIPAL_IDS" ]; then
    echo "Error: Could not determine any Agent Identities."
    echo "Please ensure the agents are deployed."
    exit 1
fi

# Convert string to array
IFS=$'\n' read -rd '' -a AGENT_ID_ARRAY <<< "$AGENT_PRINCIPAL_IDS"


# 2. Get Resource IDs (Storage, Search)
echo "Finding Storage Account..."
STORAGE_ACCOUNT_ID=$(az resource list -g "$AZURE_RESOURCE_GROUP" \
    --resource-type "Microsoft.Storage/storageAccounts" \
    --query "[0].id" \
    --output tsv)

if [ -z "$STORAGE_ACCOUNT_ID" ]; then
    echo "Error: No Storage Account found in resource group."
    exit 1
fi

echo "Finding Azure AI Search Service..."
SEARCH_SERVICE_ID=$(az resource list -g "$AZURE_RESOURCE_GROUP" \
    --resource-type "Microsoft.Search/searchServices" \
    --query "[0].id" \
    --output tsv)

# 3. Assign Roles
assign_role() {
    local role="$1"
    local scope="$2"
    local principal_id="$3"
    
    echo "Assigning role '$role'..."
    az role assignment create \
        --role "$role" \
        --assignee-object-id "$principal_id" \
        --assignee-principal-type ServicePrincipal \
        --scope "$scope" \
        --output none
}


echo "--------------------------------------------------"
echo " Applying Permissions to ${#AGENT_ID_ARRAY[@]} Identified Agents"
echo "--------------------------------------------------"

for AGENT_PRINCIPAL_ID in "${AGENT_ID_ARRAY[@]}"; do
    if [ -z "$AGENT_PRINCIPAL_ID" ]; then continue; fi

    echo "Processing Identity: $AGENT_PRINCIPAL_ID"

    for ROLE in "${ROLES[@]}"; do
        # Determine scope based on role name
        if [[ "$ROLE" == *"Storage"* ]]; then
            assign_role "$ROLE" "$STORAGE_ACCOUNT_ID" "$AGENT_PRINCIPAL_ID"
        elif [[ "$ROLE" == *"Search"* ]]; then
            if [ -n "$SEARCH_SERVICE_ID" ]; then
                assign_role "$ROLE" "$SEARCH_SERVICE_ID" "$AGENT_PRINCIPAL_ID"
            else
                echo "Skipping '$ROLE' - No Search Service found."
            fi
        else
            echo "Warning: Do not know correct scope for role '$ROLE'. Skipping."
            echo "TODO: Add logic for other resource scopes in auth_update.sh"
        fi
    done
    echo "Done with $AGENT_PRINCIPAL_ID"
    echo "--------------------------------------------------"
done

echo "Successfully updated credentials for all found agents."
