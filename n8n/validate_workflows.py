import json
import glob
import os
import sys

SUSPICIOUS_SECRETS = [
    "sk_live_",
    "ghp_",
    "AKIA",
    "password123",
    "Bearer eyJ",
]


def validate_workflow_file(filepath: str) -> bool:
    print(f"Validating workflow: {os.path.basename(filepath)}")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Check for hard-coded private secrets
    for secret in SUSPICIOUS_SECRETS:
        if secret in content:
            raise ValueError(f"Security Alert: Workflow '{filepath}' contains suspicious hardcoded secret token '{secret}'.")

    try:
        wf = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON Syntax Error in '{filepath}': {e}")

    # Validate n8n schema structure
    for key in ("name", "nodes", "connections"):
        if key not in wf:
            raise ValueError(f"Missing required n8n workflow field '{key}' in '{filepath}'")

    nodes = wf.get("nodes", [])
    node_names = set()
    for n in nodes:
        if "name" not in n or "type" not in n:
            raise ValueError(f"Node missing 'name' or 'type' in '{filepath}': {n}")
        node_names.add(n["name"])

    # Validate connections map to existing nodes
    connections = wf.get("connections", {})
    for source_node, conn_groups in connections.items():
        if source_node not in node_names:
            raise ValueError(f"Connection from unknown node '{source_node}' in '{filepath}'")
        for group_name, outputs in conn_groups.items():
            for target_list in outputs:
                for target_conn in target_list:
                    target_node = target_conn.get("node")
                    if target_node not in node_names:
                        raise ValueError(f"Connection to unknown target node '{target_node}' in '{filepath}'")

    print(f"  [OK] {wf['name']} ({len(nodes)} nodes) validated successfully.")
    return True


def main():
    workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
    files = glob.glob(os.path.join(workflows_dir, "*.json"))
    if not files:
        print("No workflow files found!")
        sys.exit(1)

    print(f"Validating {len(files)} n8n workflow JSON blueprints...\n")
    for f in files:
        validate_workflow_file(f)
    print("\nAll exported n8n workflow blueprints verified cleanly.")


if __name__ == "__main__":
    main()
