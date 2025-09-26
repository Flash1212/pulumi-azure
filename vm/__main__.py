# __main__.py
import modulepath_fixer  # noqa: F401

import os
import subprocess

from pulumi import export, log, ResourceOptions
import pulumi_azure_native as azure_native
from modules.compute import VM, EnvironmentSpecs, VMSpecs
from config import (
    add_my_public_ip_to_nsg,
    azure_location,
    resource_group_suffix,
    vnet_address_prefixes,
    subnet_address_prefixes,
    vm_specs,
)

DEBUG = os.getenv("DEBUG")
default_tags = {
    "environment": "dev",
    "created_by": "pulumi",
    "purpose": "development",
}
resource_group_name = f"{azure_location}-{resource_group_suffix}"


def generate_github_raw_url(script_rel_path):
    remote_git_url = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        capture_output=True,
        text=True,
    ).stdout.strip()

    current_git_branch = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
    ).stdout.strip()

    raw_github_url = remote_git_url.replace(
        ".git", f"/{current_git_branch}"
    ).replace("github.com", "raw.githubusercontent.com")
    return f"{raw_github_url}/{script_rel_path}"


def get_my_public_ip():
    import requests

    my_ip = requests.get("https://api.ipify.org").text
    source_address_prefix = f"{my_ip}/32"
    return source_address_prefix


def setup_network_security_group(
    azure_location: str,
    nsg_name: str,
    nsg_tags: dict,
    source_address_prefix: str,
    resource_group: azure_native.resources.ResourceGroup,
    vm_specs: list[VMSpecs],
    opts: ResourceOptions,
) -> azure_native.network.NetworkSecurityGroup:
    """
    Sets up a Network Security Group (NSG) with rules for Windows/Linux
    remote sessions, HTTP, and HTTPS access.
    """

    security_rules = []
    for vm_spec in vm_specs:
        rule_name = None
        rule_port = None
        if "windows" in vm_spec.os_type.lower():
            rule_name = "AllowRDP"
            rule_port = "3389"
            priority = 1000
        elif "linux" in vm_spec.os_type.lower():
            rule_name = "AllowSSH"
            rule_port = "22"
            priority = 1001
        else:
            raise ValueError(
                f"Unsupported OS type for VM {vm_spec.server_name}: {vm_spec.os_type}"  # noqa: E501
            )
        security_rules.append(
            azure_native.network.SecurityRuleArgs(
                name=rule_name,
                protocol="Tcp",
                source_port_range="*",
                destination_port_range=rule_port,
                source_address_prefix=source_address_prefix,
                destination_address_prefix="*",
                access="Allow",
                priority=priority,
                direction="Inbound",
            )
        )

    return azure_native.network.NetworkSecurityGroup(
        nsg_name,
        azure_native.network.NetworkSecurityGroupInitArgs(
            location=azure_location,
            resource_group_name=resource_group.name,
            security_rules=security_rules
            + [
                azure_native.network.SecurityRuleArgs(
                    name="AllowHTTP",
                    protocol="Tcp",
                    source_port_range="*",
                    destination_port_range="80",
                    source_address_prefix=source_address_prefix,
                    destination_address_prefix="*",
                    access="Allow",
                    priority=1010,
                    direction="Inbound",
                ),
                azure_native.network.SecurityRuleArgs(
                    name="AllowHTTPS",
                    protocol="Tcp",
                    source_port_range="*",
                    destination_port_range="443",
                    source_address_prefix=source_address_prefix,
                    destination_address_prefix="*",
                    access="Allow",
                    priority=1005,
                    direction="Inbound",
                ),
            ],
            tags=nsg_tags,
        ),
        opts=opts,
    )


resource_group = azure_native.resources.ResourceGroup(
    resource_name=resource_group_name,
    location=azure_location,
    tags=default_tags,
)

virtual_network = azure_native.network.VirtualNetwork(
    f"{resource_group_name}-vm-vnet",
    resource_group_name=resource_group.name,
    address_space=azure_native.network.AddressSpaceArgs(
        address_prefixes=vnet_address_prefixes,
    ),
    location=azure_location,
    tags=default_tags,
    opts=ResourceOptions(
        parent=resource_group,
    ),
)

source_address_prefix = "*"
nsg_tags = default_tags.copy()
if add_my_public_ip_to_nsg:
    nsg_tags["my_public_ip"] = get_my_public_ip()

network_security_group = setup_network_security_group(
    azure_location=azure_location,
    nsg_name=f"{resource_group_name}-vm-nsg",
    nsg_tags=nsg_tags,
    resource_group=resource_group,
    source_address_prefix=source_address_prefix,
    vm_specs=vm_specs,
    opts=ResourceOptions(parent=virtual_network),
)

subnet = azure_native.network.Subnet(
    f"{resource_group_name}-vm-subnet",
    address_prefixes=subnet_address_prefixes,
    network_security_group=azure_native.network.NetworkSecurityGroupArgs(
        id=network_security_group.id,
    ),
    resource_group_name=resource_group.name,
    virtual_network_name=virtual_network.name,
    opts=ResourceOptions(
        parent=virtual_network,
    ),
)

env_spec = EnvironmentSpecs(
    resource_group=resource_group,
    vnet=virtual_network,
    subnet=subnet,
    tags=default_tags,
)

vms = []
for vm_spec in vm_specs:
    vm = VM(
        name=vm_spec.server_name,
        vm_spec=vm_spec,
        env_spec=env_spec,
        opts=ResourceOptions(parent=subnet),
    )

    export(
        f"{vm_spec.server_name}_specs",
        {
            "ip": vm.public_ip.ip_address,
            "username": vm_spec.admin_username,
            "password": vm.password.result,
        },
    )

    if not vm_spec.script_path:
        continue

    for script_rel_path in vm_spec.script_path:
        if os.path.exists(
            os.path.join(os.path.dirname(__file__), script_rel_path)
        ):
            filename = os.path.basename(script_rel_path)
            sanitized_path = script_rel_path.replace("../", "")
            script_uri = generate_github_raw_url(sanitized_path)
            if DEBUG:
                log.info(f"Executing script: {script_uri}")

            publisher: str
            type_: str
            type_handler_version: str
            if vm_spec.os_type.lower() == "windows":
                command_to_execute = (
                    f"powershell -ExecutionPolicy Unrestricted -File {filename}"
                )
                publisher = "Microsoft.Compute"
                type_ = "CustomScriptExtension"
                type_handler_version = "1.10"
            elif vm_spec.os_type.lower() == "linux":
                command_to_execute = (
                    f"bash --noprofile --norc -eo pipefail {filename}"
                )
                publisher = "Microsoft.Azure.Extensions"
                type_ = "CustomScript"
                type_handler_version = "2.1"
            else:
                raise ValueError(
                    f"Unsupported OS type for VM {vm_spec.server_name}: {vm_spec.os_type}"  # noqa: E501
                )

            azure_native.compute.VirtualMachineExtension(
                f"{vm_spec.server_name}-{filename}-script",
                resource_group_name=env_spec.resource_group.name,
                vm_name=vm.virtual_machine.name,
                publisher=publisher,
                type=type_,
                type_handler_version=type_handler_version,
                settings={
                    "fileUris": [f"{script_uri}"],
                    "commandToExecute": command_to_execute,
                },
                opts=ResourceOptions(parent=vm.virtual_machine),
            )
