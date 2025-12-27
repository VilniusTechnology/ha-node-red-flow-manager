"""Constants for the Node-RED Flow Manager integration."""

DOMAIN = "node_flow_manager"

CONF_FLOW_ID = "flow_id"
CONF_FLOW_NAME = "flow_name"
CONF_TAB_ID = "tab_id"
CONF_PUBLIC_URL = "public_url"
CONF_PUBLIC_URL = "public_url"
CONF_LOG_LEVEL = "log_level"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 1880
DEFAULT_VERIFY_SSL = False
DEFAULT_LOG_LEVEL = "info"
DEFAULT_SCAN_INTERVAL = 120

LOG_LEVELS = {
    "debug": "Debug",
    "info": "Info",
    "warning": "Warning",
    "error": "Error",
    "critical": "Critical",
}
