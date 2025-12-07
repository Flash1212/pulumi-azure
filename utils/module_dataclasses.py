from dataclasses import dataclass, field
from typing import Optional
from pulumi import Input, Output

import configs.generated.servicebus_pkl as psb


@dataclass
class SecretsObject:
    """
    Dataclass to hold the secrets for the Azure Keyvault.
    Args:
        secrets (dict[str, Input[str]]): The secrets to store in the Azure
            Keyvault.
        origin (str): The origin of the secrets.
        purpose (str): The purpose of the secrets.
        custom_tags (dict[str, str], optional): Custom tags to add to the
            secrets. Defaults to {}.
    """

    secrets: dict[str, Input[str]]
    origin: str
    purpose: str
    custom_tags: Optional[dict[str, str]] = field(default_factory=dict)

    def __post_init__(self):
        for key, value in self.secrets.items():
            if not isinstance(value, Output):
                self.secrets[key] = Output.secret(value)


@dataclass
class ServiceBusArgs:
    """
    Dataclass to hold the arguments for creating a new Azure Service Bus.

    Args:
        location (str): The location of the Azure Service Bus Namespace.
        pkl_configs (list[psb.Namespace]): List of Pkl configurations per
            platform for the Azure Service Bus.
        resource_group (Output[str]): The name of the resource group the Azure
            Service Bus Namespace is in.
        tags (dict): Tags to add to the Azure Service Bus Namespace

    """

    location: str
    pkl_configs: list[psb.Namespace]
    resource_group_name: Output[str]
    tags: dict[str, str]
