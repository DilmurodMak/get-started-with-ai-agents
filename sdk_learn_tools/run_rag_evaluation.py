import os
import time
import json
import glob
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ConnectionType
from openai.types.evals.create_eval_jsonl_run_data_source_param import (
    CreateEvalJSONLRunDataSourceParam,
    SourceFileContent,
    SourceFileContentContent,
)

# --- 1. Setup & Config ---
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
env_path = os.path.join(workspace_root, ".azure", "mak-foundry-demo", ".env")

if os.path.exists(env_path):
    print(f"Loading environment from {env_path}")
    load_dotenv(env_path)
else:
    load_dotenv()

project_endpoint = os.environ.get("AZURE_EXISTING_AIPROJECT_ENDPOINT")
model_deployment_name = os.environ.get("AZURE_AI_AGENT_DEPLOYMENT_NAME") 

if not project_endpoint or not model_deployment_name:
    raise ValueError("Missing environment variables (Endpoint or Deployment Name).")

# Get Agent Name
agent_name = os.environ.get("AZURE_AI_AGENT_NAME")
if not agent_name:
      raise ValueError("Missing AZURE_AI_AGENT_NAME environment variable.")

print(f"Connecting to Project: {project_endpoint}")

# --- 2. Client Initialization ---
with DefaultAzureCredential() as credential:
    with AIProjectClient(endpoint=project_endpoint, credential=credential) as project_client:
        
        # Get an OpenAI client for generation
        openai_client = project_client.get_openai_client()

        # --- 4. Generate Responses (The "System" Step) ---
        input_dataset_path = os.path.join(os.path.dirname(__file__), "ground_truth_dataset.jsonl")
        eval_data_items = []
        
        print(f"Generating responses for queries in {input_dataset_path}...")
        with open(input_dataset_path, "r") as f:
            lines = f.readlines()
            
        for line in lines:
            if not line.strip(): continue
            row = json.loads(line)
            query = row["query"]
            ground_truth = row.get("ground_truth", "")
            
            time.sleep(2) # Avoid rate limits
            
            # Use 'context' if present in dataset (e.g. from previous steps), otherwise it might be empty
            # NOTE: Groundedness metric usually needs 'context'. If the agent retrieval is internal/opaque, 
            # we might not easily get the retrieved chunks unless the agent returns them (e.g. as citations).
            # For this example, we will see if we can extract citations or leave context empty/simulated.
            context = "Context handled by agent." 
            
            # 2. Generate Response using Model (Simulating the Agent)
            # We use the project's openai_client to call the deployed model
            context = "Context handled by agent."
            response_text = "Error generating response"
            try:
                # Create a conversation for this query
                conversation = openai_client.conversations.create() 
                # Chat with the agent
                response = openai_client.responses.create(
                    conversation=conversation.id, #Optional conversation context for multi-turn
                    extra_body={"agent": {"name": agent_name, "type": "agent_reference"}},
                    input=query,
                )
                response_text = response.output_text
            except Exception as e:
                print(f"Error generating response: {e}")

            print(f"  Q: {query[:30]}... -> A: {response_text[:30]}...")

            # 3. Prepare Item for Evaluation
            eval_data_items.append({
                "query": query,
                "response": response_text,
                "context": context,
                "ground_truth": ground_truth
            })

        # --- 5. Run RAG Evaluation (The "Evaluation" Step) ---
        print("\nStarting RAG Evaluation...")

        # Prepare Data Source for Eval
        # We transform our list of dicts into the format expected by the SDK
        inline_content = [
            SourceFileContentContent(item=item) for item in eval_data_items
        ]

        # Define Evaluators (Groundedness, Relevance, etc.)
        # Note: Groundedness requires 'context', 'response', 'query'
        testing_criteria = [
            {
                "type": "azure_ai_evaluator",
                "name": "groundedness",
                "evaluator_name": "builtin.groundedness",
                "initialization_parameters": {
                    "deployment_name": model_deployment_name
                },
                "data_mapping": {
                    "context": "{{item.context}}",
                    "query": "{{item.query}}",
                    "response": "{{item.response}}"
                },
            },
            {
                "type": "azure_ai_evaluator",
                "name": "relevance",
                "evaluator_name": "builtin.relevance",
                "initialization_parameters": {
                    "deployment_name": model_deployment_name
                },
                "data_mapping": {
                    "query": "{{item.query}}",
                    "response": "{{item.response}}"
                },
            }
        ]

        # Define Data Schema
        data_source_config = {
            "type": "custom",
            "item_schema": {
                "type": "object",
                "properties": {
                    "context": {"type": "string"},
                    "query": {"type": "string"},
                    "response": {"type": "string"},
                    "ground_truth": {"type": "string"},
                },
                "required": ["query", "response", "context"]
            },
            "include_sample_schema": True,
        }

        # Submit Evaluation
        try:
            eval_object = openai_client.evals.create(
                name="rag-eval-custom",
                data_source_config=data_source_config,
                testing_criteria=testing_criteria,
            )
            
            run = openai_client.evals.runs.create(
                eval_id=eval_object.id,
                name="rag-eval-run-inline",
                data_source=CreateEvalJSONLRunDataSourceParam(
                    type="jsonl",
                    source=SourceFileContent(
                        type="file_content",
                        content=inline_content
                    ),
                ),
            )
            
            print(f"Evaluation Run Submitted: {run.id}")
            print(f"Check status at: {run.report_url}")
            
            # Poll for completion
            import time
            while run.status not in ["completed", "failed", "cancelled"]:
                print(f"Status: {run.status}")
                time.sleep(5)
                run = openai_client.evals.runs.retrieve(run_id=run.id, eval_id=eval_object.id)

            print(f"Run Finished. Status: {run.status}")
            print(f"Report: {run.report_url}")

        except Exception as e:
            print(f"Evaluation failed: {e}")
