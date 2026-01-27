import os
import time
import json
import subprocess
from datetime import datetime, timezone
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from openai.types.eval_create_params import DataSourceConfigCustom
from openai.types.evals.create_eval_jsonl_run_data_source_param import CreateEvalJSONLRunDataSourceParam, SourceFileID

# --- 1. Environment Setup ---
# Load environment variables from the attached .env file
# We look for .azure/mak-fdy-demo/.env relative to the workspace root
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
env_path = os.path.join(workspace_root, ".azure", "mak-fdy-demo", ".env")

if os.path.exists(env_path):
    print(f"Loading environment from {env_path}")
    load_dotenv(env_path)
else:
    print("Warning: Specific .env file not found. Relying on existing environment variables.")
    load_dotenv()

# --- 2. Configuration & Derived Variables ---

# Project Endpoint
project_endpoint = os.environ.get("AZURE_EXISTING_AIPROJECT_ENDPOINT")
if not project_endpoint:
    raise ValueError("AZURE_EXISTING_AIPROJECT_ENDPOINT is not set.")

# Model Deployment Name (e.g., gpt-4)
model_deployment_name = os.environ.get("AZURE_AI_AGENT_DEPLOYMENT_NAME")
if not model_deployment_name:
    raise ValueError("AZURE_AI_AGENT_DEPLOYMENT_NAME is not set.")

# --- 3. Client Initialization & Execution ---

print(f"Connecting to Project: {project_endpoint}")

# Create an `AIProjectClient` and retrieve the `OpenAI` client
with DefaultAzureCredential() as credential, \
     AIProjectClient(endpoint=project_endpoint, credential=credential) as project_client, \
     project_client.get_openai_client() as openai_client:

    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')

    # --- 4. Upload Data ---
    data_file_name = "evaluate_test_data.jsonl"
    data_file_path = os.path.join(os.path.dirname(__file__), data_file_name)

    if not os.path.exists(data_file_path):
        raise FileNotFoundError(f"Data file not found at {data_file_path}")

    # Use a specific version or auto-increment to avoid conflict
    dataset_name = f"dataset-test-eval-{timestamp}"
    dataset_version = "1"

    print(f"Uploading dataset '{dataset_name}' version '{dataset_version}'...")
    try:
        dataset = project_client.datasets.upload_file(
            name=dataset_name,
            version=dataset_version,
            file_path=data_file_path,
        )
        print(f"Dataset uploaded. ID: {dataset.id}")
    except Exception as e:
        print(f"Failed to upload dataset: {e}")
        exit(1)

    # --- 5. Define Data Source & Evaluators ---

    # Define Data Source Config
    data_source_config = DataSourceConfigCustom(
        {
            "type": "custom",
            "item_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "response": {"type": "string"},
                },
                "required": [],
            },
            "include_sample_schema": True,
        }
    )

    # Define Testing Criteria (Evaluators)
    testing_criteria = [
        # Built-in Evaluator: Relevance
        {
            "type": "azure_ai_evaluator",
            "name": "relevance",
            "evaluator_name": "builtin.relevance",
            "data_mapping": {"query": "{{item.query}}", "response": "{{item.response}}"},
            "initialization_parameters": {"deployment_name": model_deployment_name},
        },
        # Built-in Evaluator: Coherence (Replacing Violence which might not be built-in supported the same way or requires specific safety setup)
        {
            "type": "azure_ai_evaluator",
            "name": "coherence",
            "evaluator_name": "builtin.coherence",
            "data_mapping": {"query": "{{item.query}}", "response": "{{item.response}}"},
            "initialization_parameters": {"deployment_name": model_deployment_name},
        }
    ]

    # --- 6. Submit Evaluation ---

    print("Creating evaluation definition...")
    try:
        evaluation = openai_client.evals.create(
            name=f"cloud-eval-{timestamp}",
            data_source_config=data_source_config,
            testing_criteria=testing_criteria,
        )
        print(f"Evaluation definition created: {evaluation.id}")

        print("Starting evaluation run...")
        run = openai_client.evals.runs.create(
            eval_id=evaluation.id,
            name=f"cloud-eval-run-{timestamp}",
            data_source=CreateEvalJSONLRunDataSourceParam(
                type="jsonl", 
                source=SourceFileID(type="file_id", id=dataset.id)
            )
        )
        print(f"Run created: {run.id}")
        
        # --- 7. Wait for Completion ---
        print("Waiting for evaluation to complete...")
        while run.status not in ["completed", "failed", "cancelled"]:
            run = openai_client.evals.runs.retrieve(run_id=run.id, eval_id=evaluation.id)
            print(f"Status: {run.status}")
            time.sleep(5)

        print("------------------------------------------------")
        print(f"Evaluation Run Finished!")
        print(f"Status: {run.status}")
        print(f"Report URL: {run.report_url}")
        print("------------------------------------------------")

        if run.status == "completed":
             # Retrieve and save output items
            try:
                output_items = list(openai_client.evals.runs.output_items.list(run_id=run.id, eval_id=evaluation.id))
                # Simple serialization for demo purposes
                json_output = json.dumps([item.model_dump() for item in output_items], indent=4, default=str)
                
                output_file = f"eval_results_{timestamp}.json"
                output_file_path = os.path.join(os.path.dirname(__file__), output_file)
                with open(output_file_path, "w") as f:
                    f.write(json_output)
                print(f"Evaluation results saved to {output_file}")
            except Exception as inner_e:
                print(f"Failed to retrieve results: {inner_e}")

    except Exception as e:
        print(f"Failed to submit evaluation: {e}")
