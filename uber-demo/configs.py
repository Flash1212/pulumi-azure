from pulumi import Config


az_native_config = Config("azure-native")
location = az_native_config.require("location")
subscription_id = az_native_config.require("subscriptionId")

func_app_configs = Config()
# Resource creation toggles
create_app_insights: bool = func_app_configs.require_bool(
    "create_app_insights"
)  # Requires log_analytics
create_event_grid: bool = func_app_configs.require_bool("create_event_grid")
create_function_app: bool = func_app_configs.require_bool("create_function_app")
create_key_vault: bool = func_app_configs.require_bool("create_key_vault")
create_log_analytics: bool = func_app_configs.require_bool(
    "create_log_analytics"
)
create_servicebus: bool = func_app_configs.require_bool("create_servicebus")
create_storage_account: bool = func_app_configs.require_bool(
    "create_storage_account"
)
# Resource names and settings
app_svc_plan_name: str = func_app_configs.require("app_svc_plan_name")
blob_names: list = func_app_configs.require_object("blob_names")
func_app_name: str = func_app_configs.require("func_app_name")
resource_group_prefix: str = func_app_configs.require("resource-group-prefix")
queue_names: list = func_app_configs.require_object("queue_names")
# Function App Settings
func_runtime_args: dict | None = func_app_configs.get_object(
    "func_runtime_args"
)
