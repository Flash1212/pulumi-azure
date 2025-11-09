from pulumi import Config


az_native_config = Config("azure-native")
location = az_native_config.require("location")
subscription_id = az_native_config.require("subscriptionId")

storage_work_configs = Config()
resource_group_prefix = storage_work_configs.require("resource-group-prefix")
container_names:list[str] = storage_work_configs.require_object("container-names")
create_container_sas: bool = storage_work_configs.get_bool("create-container-sas") or False
queue_names:list[str] = storage_work_configs.require_object("queue-names")

create_cosmos_db: bool = storage_work_configs.require_bool("create-cosmos-db")
