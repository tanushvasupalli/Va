import json
import os
import requests
from typing import Optional, Dict, Any, Union
import config
from core.mcp_client import mcp_client

def _get_headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if getattr(config, "N8N_API_KEY", ""):
        headers["X-N8N-API-KEY"] = config.N8N_API_KEY
    return headers

def search_n8n_templates(query: str = "", task: str = "", complexity: str = "") -> str:
    """
    Searches across 2,709+ curated n8n automation templates using n8n-mcp.
    
    Args:
        query: Keywords to search for (e.g. 'telegram alert', 'slack notification', 'google sheets sync').
        task: Optional task category (e.g. 'webhook_processing', 'lead_generation', 'data_sync').
        complexity: Optional complexity filter ('simple', 'medium', 'complex').
    """
    args: Dict[str, Any] = {}
    if query:
        args["query"] = query
    if task:
        args["task"] = task
        args["searchMode"] = "by_task"
    if complexity:
        args["complexity"] = complexity

    if not args:
        args["query"] = "automation"

    res = mcp_client.call_tool("search_templates", args)
    if "not found" in res.lower():
        # Fallback query
        return f"n8n Templates for '{query}':\n- Browse 2,700+ templates at https://n8n.io/workflows"
    return res

def search_n8n_nodes(query: str, category: str = "") -> str:
    """
    Searches across 2,616+ n8n nodes (core and community) to find integration capabilities.
    
    Args:
        query: Node name or action (e.g. 'telegram', 'slack', 'gmail', 'postgres', 'openai').
        category: Optional category filter.
    """
    args = {"query": query}
    if category:
        args["category"] = category
    return mcp_client.call_tool("search_nodes", args)

def get_n8n_node_schema(node_type: str) -> str:
    """
    Retrieves full properties, operations, and documentation for a specific n8n node.
    
    Args:
        node_type: The n8n node type (e.g. 'n8n-nodes-base.telegram', 'n8n-nodes-base.slack').
    """
    return mcp_client.call_tool("get_node", {"nodeType": node_type})

def validate_n8n_workflow(workflow_json_or_dict: Union[str, Dict[str, Any]]) -> str:
    """
    Validates the structure, nodes, and connections of an n8n workflow using n8n-mcp.
    """
    if isinstance(workflow_json_or_dict, str):
        try:
            parsed = json.loads(workflow_json_or_dict)
        except Exception:
            return "Invalid workflow JSON syntax."
    else:
        parsed = workflow_json_or_dict
    return mcp_client.call_tool("validate_workflow", {"workflow": parsed})

def call_n8n_webhook(path_or_url: str = "", payload: Optional[Union[Dict[str, Any], str]] = None) -> str:
    """
    Dispatches a POST request to an n8n webhook URL with a dynamic JSON payload.
    
    Args:
        path_or_url: The webhook path (e.g. '/webhook/test') or full URL. Defaults to config.N8N_WEBHOOK_URL.
        payload: Dictionary or JSON string of data to send to the workflow.
    """
    target_url = path_or_url.strip() if path_or_url and path_or_url.strip() else getattr(config, "N8N_WEBHOOK_URL", "")
    base_url = getattr(config, "N8N_BASE_URL", "http://localhost:5678").rstrip('/')

    if not target_url:
        target_url = f"{base_url}/webhook/wednesday"
    elif not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = f"{base_url}/{target_url.lstrip('/')}"

    data_payload: Dict[str, Any] = {}
    if isinstance(payload, str):
        try:
            data_payload = json.loads(payload)
        except Exception:
            data_payload = {"message": payload}
    elif isinstance(payload, dict):
        data_payload = payload
    else:
        data_payload = {"source": "wednesday"}

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
    """
    if not workflow_id_or_name:
        return "Please specify an n8n workflow name or ID."
    
    if workflow_id_or_name.startswith("http://") or workflow_id_or_name.startswith("https://"):
        return call_n8n_webhook(workflow_id_or_name, payload_data)
    
    base_url = getattr(config, "N8N_BASE_URL", "http://localhost:5678").rstrip('/')
    webhook_url = f"{base_url}/webhook/{workflow_id_or_name.lstrip('/')}"
    return call_n8n_webhook(webhook_url, payload_data)

def get_n8n_template(template_id: Union[int, str]) -> str:
    """
    Fetches the full workflow JSON template from n8n-mcp library by template ID.
    """
    try:
        t_id = int(str(template_id).strip())
    except Exception:
        return "Template ID must be a numeric ID (e.g. 4740)."
    return mcp_client.call_tool("get_template", {"templateId": t_id})

def create_and_deploy_n8n_workflow(
    name: str,
    workflow_json_or_dict: Union[str, Dict[str, Any]],
    activate: bool = True
) -> str:
    """
    Autonomously creates, saves, hosts, and activates a workflow locally in your n8n instance via REST API.
    
    Args:
        name: Name for the new workflow (e.g. 'Telegram AI News Aggregator').
        workflow_json_or_dict: Valid n8n workflow structure containing nodes, connections, settings.
        activate: Whether to immediately activate and start hosting the workflow (default True).
    """
    base_url = getattr(config, "N8N_BASE_URL", "http://localhost:5678").rstrip('/')
    api_key = getattr(config, "N8N_API_KEY", "")
    
    if not api_key:
        return f"n8n REST API key is required to autonomously deploy workflows. Please set N8N_API_KEY in your .env or via /config set N8N_API_KEY <key>."

    # Parse workflow payload
    if isinstance(workflow_json_or_dict, str):
        try:
            workflow_data = json.loads(workflow_json_or_dict)
        except Exception as e:
            return f"Invalid workflow JSON format: {e}"
    elif isinstance(workflow_json_or_dict, dict):
        workflow_data = workflow_json_or_dict
    else:
        return "Workflow must be provided as a JSON string or dict."

    # If full template object passed, extract workflow structure
    if "template" in workflow_data and isinstance(workflow_data["template"], dict):
        workflow_data = workflow_data["template"]
    if "workflow" in workflow_data and isinstance(workflow_data["workflow"], dict):
        workflow_data = workflow_data["workflow"]

    payload = {
        "name": name,
        "nodes": workflow_data.get("nodes", []),
        "connections": workflow_data.get("connections", {}),
        "settings": workflow_data.get("settings", {}),
        "active": False # Create first, then activate
    }

    # 1. First validate via n8n-mcp
    val_res = validate_n8n_workflow(payload)
    if "error" in val_res.lower() and "invalid" in val_res.lower():
        # Soft validation warning log
        pass

    # 2. Deploy to n8n REST API
    create_url = f"{base_url}/api/v1/workflows"
    try:
        res = requests.post(create_url, json=payload, headers=_get_headers(), timeout=15)
        if res.status_code not in (200, 201):
            return f"Failed to create workflow in n8n (HTTP {res.status_code}): {res.text[:300]}"
        
        created = res.json()
        wf_id = created.get("id") or created.get("data", {}).get("id")
        wf_name = created.get("name") or name

        # 3. Autonomously activate workflow if requested
        if activate and wf_id:
            act_url = f"{base_url}/api/v1/workflows/{wf_id}/activate"
            act_res = requests.post(act_url, headers=_get_headers(), timeout=10)
            status_text = "ACTIVE & HOSTED LOCALLY" if act_res.status_code in (200, 201) else "SAVED (Inactive)"
        else:
            status_text = "SAVED (Inactive)"

        return f"✅ Workflow '{wf_name}' (ID: `{wf_id}`) created successfully!\nStatus: *{status_text}*\nAccess locally at: {base_url}/workflow/{wf_id}"
    except Exception as e:
        return f"Error communicating with local n8n instance at {create_url}: {e}"

def activate_n8n_workflow(workflow_id: str) -> str:
    """Activates an existing workflow in n8n so it starts listening/running."""
    base_url = getattr(config, "N8N_BASE_URL", "http://localhost:5678").rstrip('/')
    url = f"{base_url}/api/v1/workflows/{workflow_id.strip()}/activate"
    try:
        res = requests.post(url, headers=_get_headers(), timeout=10)
        if res.status_code in (200, 201):
            return f"✅ Workflow `{workflow_id}` is now ACTIVE and running locally."
        return f"Failed to activate workflow `{workflow_id}`: HTTP {res.status_code} - {res.text[:200]}"
    except Exception as e:
        return f"Connection error to n8n: {e}"

def deactivate_n8n_workflow(workflow_id: str) -> str:
    """Deactivates a running workflow in n8n."""
    base_url = getattr(config, "N8N_BASE_URL", "http://localhost:5678").rstrip('/')
    url = f"{base_url}/api/v1/workflows/{workflow_id.strip()}/deactivate"
    try:
        res = requests.post(url, headers=_get_headers(), timeout=10)
        if res.status_code in (200, 201):
            return f"⏸ Workflow `{workflow_id}` has been deactivated."
        return f"Failed to deactivate workflow `{workflow_id}`: HTTP {res.status_code} - {res.text[:200]}"
    except Exception as e:
        return f"Connection error to n8n: {e}"

def delete_n8n_workflow(workflow_id: str) -> str:
    """Deletes a workflow from n8n."""
    base_url = getattr(config, "N8N_BASE_URL", "http://localhost:5678").rstrip('/')
    url = f"{base_url}/api/v1/workflows/{workflow_id.strip()}"
    try:
        res = requests.delete(url, headers=_get_headers(), timeout=10)
        if res.status_code in (200, 204):
            return f"🗑 Workflow `{workflow_id}` deleted successfully from n8n."
        return f"Failed to delete workflow `{workflow_id}`: HTTP {res.status_code} - {res.text[:200]}"
    except Exception as e:
        return f"Connection error to n8n: {e}"

def list_n8n_workflows() -> str:
    """
    Fetches the list of active workflows from n8n REST API.
    """
    base_url = getattr(config, "N8N_BASE_URL", "http://localhost:5678").rstrip('/')
    api_key = getattr(config, "N8N_API_KEY", "")
    if not api_key:
        return f"n8n is running at {base_url}. To list workflows from the REST API, set N8N_API_KEY in your .env file or Telegram /config."
    
    url = f"{base_url}/api/v1/workflows"
    try:
        response = requests.get(url, headers=_get_headers(), timeout=10)
        if response.status_code == 200:
            data = response.json()
            workflows = data.get("data", [])
            if not workflows:
                return "No workflows found in your n8n workspace."
            summary = [f"- {w.get('name')} (ID: `{w.get('id')}`, Active: {w.get('active')})" for w in workflows[:25]]
            return f"⚡ *Active n8n Workflows ({len(workflows)}):*\n" + "\n".join(summary)
        return f"n8n API returned status {response.status_code}: {response.text[:200]}"
    except Exception as e:
        return f"Could not connect to n8n API at {url}: {e}"

