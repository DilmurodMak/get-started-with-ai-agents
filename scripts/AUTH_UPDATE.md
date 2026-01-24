# Automated Agent Authentication Update

This document describes the automated mechanism used to assign necessary Azure role assignments (permissions) to the Azure AI Agent's identity.

## Problem Context

When deploying Azure AI Agents, especially when moving from a "Development" (Draft) state to a "Published" state (or re-deploying via `azd up`), the Agent often gets a new System Assigned Identity (Service Principal). This is known as the "Agent Identity Blueprint".

Because the identity changes, any permissions previously manually assigned (like access to Storage Accounts or AI Search) are lost, causing the agent to fail when trying to access tools or data.

## Solution: `auth_update.sh`

The script `scripts/auth_update.sh` handles this automatically. It is designed to:
1.  **Find the correct Identity**: Dynamic lookup of the most recently created "Agent Identity" associated with the project.
2.  **Restore Permissions**: Automatically assigns a configured list of roles to that identity.

### How it Works

1.  **Identity Discovery**:
    -   The script looks for Service Principals matching the pattern: `<AccountName>-<ProjectName>-AgentIdentity`.
    -   Since multiple identities might exist (e.g., one for Dev, one for Published), it sorts them by `createdDateTime` and selects the **most result** one. This ensures we target the active "Published" agent.
    -   Dynamic sorting ensures we don't accidentally update an old or unused "Draft" identity.

2.  **Role Assignment**:
    -   The script contains a configurable list of roles (array `ROLES`).
    -   It iterates through this list and assigns each role to the discovered identity.
    -   It automatically detects the correct "Scope" for the role:
        -   **Storage Roles** are assigned to the Storage Account in the Resource Group.
        -   **Search Roles** are assigned to the Azure AI Search Service (if one exists).

### Configuration

You can customize which roles are assigned by editing `scripts/auth_update.sh`.
Look for the `ROLES` array at the top of the file:

```bash
ROLES=(
    "Storage Blob Data Contributor"
    "Search Index Data Reader"
    "Search Index Data Contributor"
    "Search Service Contributor"
    # Add new roles here...
)
```

### Usage

#### Automatic (Recommended)
This script is hooked into the deployment pipeline via `scripts/postdeploy.sh`.
Every time you run:
```bash
azd up
```
The permissions will be automatically updated at the end of the deployment.

#### Manual
If you suspect permissions are broken or you want to force an update without a full deployment:

1.  Open a terminal.
2.  Load your environment variables (if using `azd`):
    ```bash
    azd env get-values > .env
    source .env
    ```
3.  Run the script:
    ```bash
    ./scripts/auth_update.sh
    ```
