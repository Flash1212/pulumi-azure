from pulumi import Config


az_native_config = Config("azure-native")
location = az_native_config.require("location")
subscription_id = az_native_config.require("subscriptionId")

func_app_configs = Config()
resource_group_prefix = func_app_configs.require("resource-group-prefix")
app_svc_plan_name = func_app_configs.require("app_svc_plan_name")
func_app_name = func_app_configs.require("func_app_name")
