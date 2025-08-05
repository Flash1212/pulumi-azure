# __main__.py
import modulepath_fixer  # noqa: F401

import os
import subprocess

from pulumi import export, log, ResourceOptions
import pulumi_azure_native as azure_native
from modules.vm import CreateVM, EnvironmentSpecs
from config import (
    add_my_public_ip_to_nsg,
    azure_location,
    resource_group_suffix,
    vnet_address_prefixes,
    subnet_address_prefixes,
    vm_specs,
)

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

network_security_group = azure_native.network.NetworkSecurityGroup(
    f"{resource_group_name}-vm-nsg",
    azure_native.network.NetworkSecurityGroupInitArgs(
        location=azure_location,
        resource_group_name=resource_group.name,
        security_rules=[
            azure_native.network.SecurityRuleArgs(
                name="AllowRDP",
                protocol="Tcp",
                source_port_range="*",
                destination_port_range="3389",
                source_address_prefix=source_address_prefix,
                destination_address_prefix="*",
                access="Allow",
                priority=1000,
                direction="Inbound",
            ),
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
        tags=default_tags,
    ),
    opts=ResourceOptions(parent=resource_group),
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
    vm = CreateVM(
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
            log.info(f"Executing script: {script_uri}")
            azure_native.compute.VirtualMachineExtension(
                f"{vm_spec.server_name}-{filename}-script",
                resource_group_name=env_spec.resource_group.name,
                vm_name=vm.virtual_machine.name,
                publisher="Microsoft.Compute",
                type="CustomScriptExtension",
                type_handler_version="1.10",
                settings={
                    "fileUris": [f"{script_uri}"],
                    "commandToExecute": f"powershell -ExecutionPolicy Unrestricted -File {filename}",  # noqa: E501
                },
                opts=ResourceOptions(parent=vm.virtual_machine),
            )
