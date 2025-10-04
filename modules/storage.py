from pulumi import ComponentResource, Output, ResourceOptions
from pulumi_azure_native import storage
from attr import dataclass, field
from typing import Optional


@dataclass
class CosmosDBArgs:
    resource_prefix: str
    resource_group_name: Output[str]
    cosmos_account_args: dict
    tags: dict = field(factory=dict)


@dataclass
class StorageArgs:
    resource_prefix: str
    resource_group_name: Output[str]
    storage_account_args: dict
    tags: dict = field(factory=dict)
    storage_blob_properties_args: Optional[dict] = None
    storage_blob_container_args: Optional[dict] = None
    storage_queue_args: Optional[dict] = None


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
    )
    public_network_access: storage.PublicNetworkAccess = (
        storage.PublicNetworkAccess.ENABLED
    )
    sku: storage.SkuArgs = storage.SkuArgs(name=storage.SkuName.STANDARD_LRS)


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

        self.storage_account = storage.StorageAccount(
            resource_name=f"{args.resource_prefix}storacct",
            **args.storage_account_args,
            opts=self.opts,
        )
        self.__get_keys_and_string(
            account_name=self.storage_account.name,
            resource_group_name=args.resource_group_name,
        )

        if args.storage_blob_properties_args:
            self.storage_blob_svc_props = storage.BlobServiceProperties(
                resource_name=f"{args.resource_prefix}-blob-props",
                **{
                    **args.storage_blob_properties_args,
                    "account_name": self.storage_account.name,
                },
                opts=ResourceOptions(parent=self.storage_account),
            )

        if args.storage_blob_container_args:
            self.storage_blob_container = storage.BlobContainer(
                resource_name=f"{args.resource_prefix}-container",
                **{
                    **args.storage_blob_container_args,
                    "account_name": self.storage_account.name,
                },
                opts=ResourceOptions(
                    parent=self.storage_blob_svc_props
                    if self.storage_blob_svc_props
                    else self.storage_account
                ),
            )

            self.storage_blob_container_url = Output.concat(
                self.storage_account.primary_endpoints.blob,
                self.storage_blob_container.name,
            )

        if args.storage_queue_args:
            self.storage_queue = storage.Queue(
                resource_name=f"{args.resource_prefix}-queue",
                **{
                    **args.storage_queue_args,
                    "account_name": self.storage_account.name,
                },
                opts=ResourceOptions(parent=self.storage_account),
            )

        self.register_outputs({})

    def __get_keys_and_string(
        self, account_name: Output[str], resource_group_name: Output[str]
    ) -> None:
        self.storage_account_keys: Output[
            storage.ListStorageAccountKeysResult
        ] = Output.secret(
            storage.list_storage_account_keys_output(
                account_name=account_name,
                resource_group_name=resource_group_name,
            )
        )
        self.primary_key: Output[str] = Output.secret(
            self.storage_account_keys.apply(lambda sak: sak.keys[0].value)
        )
        self.storage_connection_string: Output[str] = Output.secret(
            Output.concat(
                "DefaultEndpointsProtocol=https;AccountName=",
                self.storage_account.name,
                ";AccountKey=",
                Output.secret(self.primary_key),
            )
        )
