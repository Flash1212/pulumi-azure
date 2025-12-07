from typing import Optional

from attr import dataclass, field
from pulumi import ComponentResource, InvokeOptions, Output, ResourceOptions
from pulumi_azure_native import cosmosdb, storage

from utils.module_dataclasses import SecretsObject


@dataclass
class CosmosComponentArgs:
    name: str
    args: dict


@dataclass
class CosmosDBArgs:
    resource_group_name: Output[str]
    cosmos_account_args: CosmosComponentArgs
    tags: dict = field(factory=dict)


@dataclass
class StorageComponentArgs:
    name: str
    args: dict


@dataclass
class StorageArgs:
    resource_group_name: Output[str]
    storage_account_args: StorageComponentArgs
    tags: dict = field(factory=dict)
    storage_blob_container_args: Optional[list[StorageComponentArgs]] = None
    storage_blob_properties_args: Optional[StorageComponentArgs] = None
    storage_container_sas_args: Optional[list[StorageComponentArgs]] = None
    storage_queue_args: Optional[list[StorageComponentArgs]] = None


class StorageAccountDefaults:
    """
    A set of predefined Azure Storage Account property configurations. If
    `use_storage_account_defaults == True` these properties will be applied
    to the `StorageArgs.storage_account` property for sub properties which are
    not already configured.
    """

    access_tier: storage.AccessTier = storage.AccessTier.HOT
    allow_blob_public_access: bool = False
    allow_shared_key_access: bool = False
    dns_endpoint_type: str = "Standard"
    kind: storage.Kind = storage.Kind.STORAGE_V2
    minimum_tls_version: storage.MinimumTlsVersion = (
        storage.MinimumTlsVersion.TLS1_2
    )
    network_rule_set: storage.NetworkRuleSetArgs = storage.NetworkRuleSetArgs(
        bypass="AzureServices",
        default_action=storage.DefaultAction.ALLOW,
        ip_rules=[],
        virtual_network_rules=[],
    )
    public_network_access: storage.PublicNetworkAccess = (
        storage.PublicNetworkAccess.ENABLED
    )
    sku: storage.SkuArgs = storage.SkuArgs(name=storage.SkuName.STANDARD_LRS)


class CosmosNoSQL(ComponentResource):
    """
    Create a Storage Account with specified components.
    """

    def __init__(
        self,
        name: str,
        args: CosmosDBArgs,
        opts: ResourceOptions,
    ):
        super().__init__("flash1212:storage:StorageChain", name, None, opts)

        self.opts = ResourceOptions.merge(opts, ResourceOptions(parent=self))

        self.cosmos_account = cosmosdb.DatabaseAccount(
            resource_name=args.cosmos_account_args.name,
            resource_group_name=args.resource_group_name,
            **args.cosmos_account_args.args,
            tags={
                **args.tags,
                "defaultExperience": "Core (SQL)",
                "hidden-workload-type": "Learning",
                "hidden-cosmos-mmspecial": "",
            },
            opts=self.opts,
        )

        self.__get_keys_and_string(
            account_name=self.cosmos_account.name,
            resource_group_name=args.resource_group_name,
        )

    def __get_keys_and_string(
        self, account_name: Output[str], resource_group_name: Output[str]
    ) -> None:
        self.cosmos_account_keys: Output[
            cosmosdb.ListDatabaseAccountKeysResult
        ] = Output.secret(
            cosmosdb.list_database_account_keys_output(
                account_name=account_name,
                resource_group_name=resource_group_name,
            )
        )
        self.primary_master_key: Output[str] = Output.secret(
            self.cosmos_account_keys.apply(lambda sak: sak.primary_master_key)
        )
        self.primary_readonly_master_key: Output[str] = Output.secret(
            self.cosmos_account_keys.apply(
                lambda sak: sak.primary_readonly_master_key
            )
        )
        self.connection_strings: Output[
            cosmosdb.ListDatabaseAccountConnectionStringsResult
        ] = Output.secret(
            cosmosdb.list_database_account_connection_strings_output(
                account_name=account_name,
                resource_group_name=resource_group_name,
            )
        )


class StorageChain(ComponentResource):
    """
    Create a Storage Account with specified components.
    """

    def __init__(
        self,
        name: str,
        args: StorageArgs,
        opts: ResourceOptions,
    ):
        super().__init__("flash1212:storage:StorageChain", name, None, opts)

        self.opts = ResourceOptions.merge(opts, ResourceOptions(parent=self))
        self.storage_blob_svc_props = None
        self.storage_blob_containers: dict[str, storage.BlobContainer] = {}
        self.storage_queues: dict[str, storage.Queue] = {}
        self.storage_sas_urls: dict[str, Output[dict[str, Output[str]]]] = {}
        self.storage_secrets: SecretsObject

        self.storage_account = storage.StorageAccount(
            resource_name=args.storage_account_args.name,
            **args.storage_account_args.args,
            opts=self.opts,
        )

        if args.storage_blob_properties_args:
            self.storage_blob_svc_props = storage.BlobServiceProperties(
                resource_name=args.storage_blob_properties_args.name,
                **{
                    **args.storage_blob_properties_args.args,
                    "account_name": self.storage_account.name,
                },
                opts=ResourceOptions(parent=self.storage_account),
            )

        if args.storage_blob_container_args:
            for container in args.storage_blob_container_args:
                self.storage_blob_containers[container.name] = (
                    storage.BlobContainer(
                        resource_name=container.name,
                        **{
                            **container.args,
                            "account_name": self.storage_account.name,
                        },
                        opts=ResourceOptions(
                            parent=self.storage_blob_svc_props
                            if self.storage_blob_svc_props
                            else self.storage_account
                        ),
                    )
                )

        sas_secrets = {}
        if args.storage_container_sas_args:
            for sas in args.storage_container_sas_args:
                sas_token_result = (
                    storage.list_storage_account_service_sas_output(
                        **{
                            **sas.args,
                            "account_name": self.storage_account.name,
                        },
                        opts=InvokeOptions(parent=self.storage_account),
                    )
                )
                sas_token = sas_token_result.apply(
                    lambda r: r.service_sas_token
                )
                sas_secrets[f"{sas.name}_sas_token"] = Output.secret(sas_token)
                sas_secrets[f"{sas.name}_sas_url"] = Output.secret(
                    Output.concat(
                        self.storage_account.primary_endpoints.blob,
                        sas.name,
                        "?",
                        sas_token,
                    )
                )

        if args.storage_queue_args:
            for queue in args.storage_queue_args:
                self.storage_queues[queue.name] = storage.Queue(
                    resource_name=queue.name,
                    **{
                        **queue.args,
                        "account_name": self.storage_account.name,
                    },
                    opts=ResourceOptions(parent=self.storage_account),
                )

        self.__get_and_set_secrets(
            account_name=self.storage_account.name,
            resource_group_name=args.resource_group_name,
            sas_secrets=sas_secrets,
        )

        self.register_outputs({})

    def __get_and_set_secrets(
        self,
        account_name: Output[str],
        resource_group_name: Output[str],
        sas_secrets: dict[str, Output[str]] = {},
    ) -> None:
        self.storage_account_keys: Output[
            storage.ListStorageAccountKeysResult
        ] = Output.secret(
            storage.list_storage_account_keys_output(
                account_name=account_name,
                resource_group_name=resource_group_name,
            )
        )
        primary_key: Output[str] = Output.secret(
            self.storage_account_keys.apply(lambda sak: sak.keys[0].value)
        )
        secondary_key: Output[str] = Output.secret(
            self.storage_account_keys.apply(lambda sak: sak.keys[1].value)
        )
        self.storage_connection_string: Output[str] = Output.concat(
            "DefaultEndpointsProtocol=https;AccountName=",
            self.storage_account.name,
            ";AccountKey=",
            Output.secret(primary_key),
        )

        self.storage_secrets = SecretsObject(
            secrets={
                "PrimaryStorageAccountKey": primary_key,
                "SecondaryStorageAccountKey": secondary_key,
                "StorageConnectionString": self.storage_connection_string,
                **sas_secrets,
            },
            origin="automation",
            purpose="storage_account_secrets",
        )
