import json
import requests
from typing import Optional, Dict, Any, Union
import config

def _get_headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if config.N8N_API_KEY:
        headers["X-N8N-API-KEY"] = config.N8N_API_KEY
    return headers

def call_n8n_webhook(path_or_url: str = "", payload: Optional[Union[Dict[str, Any], str]] = None) -> str:
    """
    Dispatches a POST request to an n8n webhook URL with a dynamic JSON payload.
    
    Args:
        path_or_url: The webhook path (e.g. '/webhook/test') or full URL. Defaults to config.N8N_WEBHOOK_URL.
        payload: Dictionary or JSON string of data to send to the workflow.
    """
    target_url = path_or_url.strip() if path_or_url and path_or_url.strip() else config.N8N_WEBHOOK_URL
    if not target_url:
        target_url = f"{config.N8N_BASE_URL.rstrip('/')}/webhook/wednesday"
    elif not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = f"{config.N8N_BASE_URL.rstrip('/')}/{target_url.lstrip('/')}"

    data_payload: Dict[str, Any] = {}
    if isinstance(payload, str):
        try:
            data_payload = json.loads(payload)
        except Exception:
            data_payload = {"message": payload}
    elif isinstance(payload, dict):
        data_payload = payload
    else:
        data_payload = {"source": "wednesday", "timestamp": config.time.time() if hasattr(config, "time") else 0}

    try:
        response = requests.post(target_url, json=data_payload, headers=_get_headers(), timeout=15)
        if response.status_code in (200, 201):
            try:
                res_json = response.json()
                return f"n8n webhook executed successfully: {json.dumps(res_json, default=str)}"
            except Exception:
                return f"n8n webhook executed successfully (Status {response.status_code}): {response.text[:200]}"
        return f"n8n webhook returned HTTP {response.status_code}: {response.text[:200]}"
    except Exception as e:
        return f"Failed to call n8n webhook at {target_url}: {e}"

def trigger_n8n_workflow(workflow_id_or_name: str, payload_data: Optional[Union[Dict[str, Any], str]] = None) -> str:
    """
    Triggers a specific n8n workflow by name or ID.
    
    Args:
        workflow_id_or_name: The identifier or webhook slug of the n8n workflow.
        payload_data: Data payload to pass into the workflow.
    """
    if not workflow_id_or_name:
        return "Please specify an n8n workflow name or ID."
    
    # If full URL was provided, delegate directly
    if workflow_id_or_name.startswith("http://") or workflow_id_or_name.startswith("https://"):
        return call_n8n_webhook(workflow_id_or_name, payload_data)
    
    # Try calling webhook slug first
    webhook_url = f"{config.N8N_BASE_URL.rstrip('/')}/webhook/{workflow_id_or_name.lstrip('/')}"
    return call_n8n_webhook(webhook_url, payload_data)

def list_n8n_workflows() -> str:
    """
    Fetches the list of active workflows from n8n REST API.
    Requires N8N_API_KEY to be set in configuration.
    """
    if not config.N8N_API_KEY:
        return f"n8n base URL is configured at {config.N8N_BASE_URL}. To query the REST API, please set N8N_API_KEY in your .env file."
    
    url = f"{config.N8N_BASE_URL.rstrip('/')}/api/v1/workflows"
    try:
        response = requests.get(url, headers=_get_headers(), timeout=10)
        if response.status_code == 200:
            data = response.json()
            workflows = data.get("data", [])
            if not workflows:
                return "No workflows found in your n8n workspace."
            summary = [f"- {w.get('name')} (ID: {w.get('id')}, Active: {w.get('active')})" for w in workflows[:15]]
            return "Active n8n Workflows:\n" + "\n".join(summary)
        return f"n8n API returned status {response.status_code}: {response.text[:200]}"
    except Exception as e:
        return f"Could not connect to n8n API at {url}: {e}"
