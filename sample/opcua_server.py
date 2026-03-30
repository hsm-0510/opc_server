import json
import time
from pathlib import Path
from typing import Any

from opcua import Server, ua


def load_json_file(path: str) -> dict:
    """
    Load JSON from file.
    Also supports the case where the whole JSON object was saved as a quoted string.
    """
    raw = Path(path).read_text(encoding="utf-8").strip()
    data = json.loads(raw)

    # Handles case like:
    # "{ \"server\": { ... } }"
    if isinstance(data, str):
        data = json.loads(data)

    return data


def get_default_value(tag_type: str) -> Any:
    """
    Return a Python default value based on config tag type.
    """
    t = (tag_type or "string").strip().lower()

    if t in ["string", "str"]:
        return ""
    elif t in ["bool", "boolean"]:
        return False
    elif t in ["int", "integer", "int32", "long", "int64"]:
        return 0
    elif t in ["float", "double"]:
        return 0.0
    else:
        return ""


def build_opcua_server(server_config_path="../config/serverConfig.json",
                       weighbridge_config_path="../config/weighbridgeConfig.json"):
    # Load configs
    server_cfg = load_json_file(server_config_path)
    wb_cfg = load_json_file(weighbridge_config_path)

    # Read server config
    server_info = server_cfg.get("server", {})
    ip = server_info.get("ip", "127.0.0.1")
    port = server_info.get("port", 4840)
    server_name = server_info.get("name", "OPC UA Server")

    # Create OPC UA server
    server = Server()
    endpoint = f"opc.tcp://{ip}:{port}/pso/weighbridge/"
    server.set_endpoint(endpoint)
    server.set_server_name(server_name)

    # Register namespace
    uri = "urn:pso:smart-weighbridge"
    idx = server.register_namespace(uri)

    # Root Objects node
    objects = server.get_objects_node()

    # Add one top-level object
    root_obj = objects.add_object(idx, server_name)

    # Store created variable nodes if you want to update them later
    node_map = {}

    # Build category/tag structure
    for category in wb_cfg.get("categories", []):
        category_name = category.get("name", "UnnamedCategory")
        category_obj = root_obj.add_object(idx, category_name)

        for tag in category.get("tags", []):
            tag_name = tag.get("name", "UnnamedTag")
            tag_type = tag.get("type", "string")
            default_value = get_default_value(tag_type)

            var = category_obj.add_variable(idx, tag_name, default_value)
            var.set_writable()  # writable from OPC UA clients
            node_map[f"{category_name}.{tag_name}"] = var

    return server, node_map, endpoint, uri, server_name


if __name__ == "__main__":
    server, node_map, endpoint, uri, server_name = build_opcua_server()

    try:
        server.start()
        print("OPC UA Server started")
        print(f"Server Name : {server_name}")
        print(f"Endpoint    : {endpoint}")
        print(f"Namespace   : {uri}")

        # Example initial values
        # node_map["Entrance_XK3190_DS8.gross_weight_WB1"].set_value("0")
        # node_map["Waveshare_Monitoring.entranceLB_status"].set_value("OFF")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("Stopping server...")
    finally:
        server.stop()
        print("Server stopped")