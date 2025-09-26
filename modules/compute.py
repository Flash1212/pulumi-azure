from typing import Optional
from attr import dataclass, field
import re

from pulumi import ComponentResource, ResourceOptions
from pulumi_azure_native import (
    compute as az_compute,
    network as az_network,
    resources as az_resources,
)
from pulumi_random import RandomPassword


@dataclass
class EnvironmentSpecs:
    resource_group: az_resources.ResourceGroup
    vnet: az_network.VirtualNetwork
    subnet: az_network.Subnet
    tags: Optional[dict] = None


@dataclass
class VMSpecs:
    admin_username: str
    admin_password_version: str
    disk_size_gb: int
    name: str
    offer: str
    publisher: str
    server_name: str
    size: str
    sku: str
    os_type: str
    version: str
    script_path: Optional[list[str]] = field(factory=list)

    def __attrs_post_init__(self):
        if not re.match(r"^[A-Za-z0-9\-]+$", self.server_name):
            raise ValueError(
                f"server_name '{self.server_name}' contains invalid characters. Only letters, numbers, and hyphens are allowed."  # noqa: E501
            )


class VM(ComponentResource):
    """
    Create a Virtual Machine with specified configurations.
    """

    def __init__(
        self,
        name: str,
        vm_spec: VMSpecs,
        env_spec: EnvironmentSpecs,
        opts: ResourceOptions,
    ):
        super().__init__("flash1212:compute:VM", name, None, opts)

        self.opts = ResourceOptions.merge(opts, ResourceOptions(parent=self))

        self.public_ip = az_network.PublicIPAddress(
            f"{vm_spec.server_name}-public-ip",
            resource_group_name=env_spec.resource_group.name,
            public_ip_allocation_method="Dynamic",
            opts=self.opts,
            tags=env_spec.tags,
        )

        self.network_interface = az_network.NetworkInterface(
            f"{vm_spec.server_name}-nic",
            resource_group_name=env_spec.resource_group.name,
            ip_configurations=[
                az_network.NetworkInterfaceIPConfigurationArgs(
                    name=f"{vm_spec.server_name}-ipconfig",
                    subnet=az_network.SubnetArgs(
                        id=env_spec.subnet.id,
                    ),
                    private_ip_allocation_method="Dynamic",
                    public_ip_address=az_network.PublicIPAddressArgs(
                        id=self.public_ip.id,
                    ),
                )
            ],
            opts=self.opts,
            tags=env_spec.tags,
        )

        self.password = RandomPassword(
            f"{vm_spec.server_name}-basic-auth-{vm_spec.admin_username}-password",
            length=14,
            keepers={"version": vm_spec.admin_password_version},
            lower=True,
            upper=True,
            special=True,
            override_special="!#%^*_+=-./?~",
            numeric=True,
            opts=self.opts,
        )

        self.virtual_machine = az_compute.VirtualMachine(
            f"{vm_spec.server_name}-vm",
            resource_group_name=env_spec.resource_group.name,
            network_profile=az_compute.NetworkProfileArgs(
                network_interfaces=[
                    az_compute.NetworkInterfaceReferenceArgs(
                        id=self.network_interface.id,
                        primary=True,
                    )
                ]
            ),
            hardware_profile=az_compute.HardwareProfileArgs(
                vm_size=vm_spec.size,
            ),
            os_profile=az_compute.OSProfileArgs(
                computer_name=vm_spec.server_name,
                admin_username=vm_spec.admin_username,
                admin_password=self.password.result,
            ),
            storage_profile=az_compute.StorageProfileArgs(
                os_disk=az_compute.OSDiskArgs(
                    name=f"{vm_spec.server_name}-os-disk",
                    caching=az_compute.CachingTypes.READ_WRITE,
                    create_option=az_compute.DiskCreateOption.FROM_IMAGE,
                    managed_disk=az_compute.ManagedDiskParametersArgs(
                        storage_account_type=az_compute.StorageAccountTypes.STANDARD_LRS,
                    ),
                ),
                image_reference=az_compute.ImageReferenceArgs(
                    publisher=vm_spec.publisher,
                    offer=vm_spec.offer,
                    sku=vm_spec.sku,
                    version=vm_spec.version,
                ),
            ),
            opts=self.opts,
            tags=env_spec.tags,
        )

        self.register_outputs({})
