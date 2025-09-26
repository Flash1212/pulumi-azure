from modules.compute import VMSpecs
import pulumi

config = pulumi.Config()

# Environment configuration
azure_location: str = config.require("location")
resource_group_suffix: str = config.require("resource_group_suffix")
vnet_address_prefixes: list[str] = config.require_object(
    "vnet_address_prefixes"
)
subnet_address_prefixes: list[str] = config.require_object(
    "subnet_address_prefixes"
)
add_my_public_ip_to_nsg: bool = config.require_bool("add_my_public_ip_to_nsg")

# VM specifications
vm_specs = [VMSpecs(**spec) for spec in config.require_object("vm_specs")]
