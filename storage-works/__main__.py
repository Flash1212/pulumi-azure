# __main__.py
"""
Pulumi program to create Azure App Functions
"""

from typing import Type
from datetime import datetime, timedelta, timezone
import modulepath_fixer  # noqa: F401

from configs import (
    container_names,
    create_container_sas,
    create_cosmos_db,
    location,
    queue_names,
    resource_group_prefix,
    subscription_id,
)
from pulumi import export, Output, ResourceOptions
from pulumi_azuread import get_client_config
from pulumi_azure_native import (
    authorization,
    cosmosdb,
    managedidentity,
    resources,
    storage,
)

from modules.storage import (
    CosmosDBArgs,
    CosmosNoSQL,
    CosmosComponentArgs,
    StorageChain,
    StorageArgs,
    StorageAccountDefaults,
    StorageComponentArgs,
)


def get_defaults(storage_defaults_class: Type[StorageAccountDefaults]) -> dict:
    return {
        k: v
        for k, v in vars(storage_defaults_class).items()
        if not k.startswith("__") and not callable(v)
    }


### Setup Resource Group
resource_group = resources.ResourceGroup(f"{resource_group_prefix}-{location}")
default_opts = ResourceOptions(parent=resource_group)
default_tags = {"purpose": "az-204"}
resource_prefix = "flashy"

### Setup Storage
storage_account_args = StorageComponentArgs(
    name=f"{resource_prefix}storacct",
    args={
        **get_defaults(StorageAccountDefaults),
        "location": location,
        "resource_group_name": resource_group.name,
        "allow_blob_public_access": True,
        "allow_shared_key_access": True,
    },
)

storage_blob_container_args = [
    StorageComponentArgs(
        name=name,
        args={
            "public_access": storage.PublicAccess.NONE,
            "resource_group_name": resource_group.name,
        },
    )
    for name in container_names
]

storage_container_sas_args = []
if create_container_sas:
    start_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    expiry_time = (datetime.now(timezone.utc) + timedelta(days=1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    storage_container_sas_args = [
        StorageComponentArgs(
            name=name,
            args={
                "canonicalized_resource": Output.concat(
                    "/blob/", storage_account_args.name, f"/{name}"
                ),
                "permissions": storage.Permissions.R,
                "protocols": storage.HttpProtocol.HTTPS,
                "resource_group_name": resource_group.name,
                "resource": storage.SignedResource.C,
                "shared_access_start_time": start_time,
                "shared_access_expiry_time": expiry_time,
            },
        )
        for name in container_names
    ]

storage_queue_args = [
    StorageComponentArgs(
        name=name,
        args={"resource_group_name": resource_group.name},
    )
    for name in queue_names
]

storage = StorageChain(
    name=f"{resource_prefix}-storage",
    args=StorageArgs(
        resource_group_name=resource_group.name,
        storage_account_args=storage_account_args,
        storage_blob_container_args=storage_blob_container_args,
        storage_queue_args=storage_queue_args,
        storage_container_sas_args=storage_container_sas_args,
        tags=default_tags,
    ),
    opts=default_opts,
)

storage_blob_endpoints = {
    name: Output.concat(
        storage.storage_account.primary_endpoints.blob,
        container.name,
    )
    for name, container in storage.storage_blob_containers.items()
}
storage_queue_endpoints = {
    name: Output.concat(
        storage.storage_account.primary_endpoints.queue,
        queue.name,
    )
    for name, queue in storage.storage_queues.items()
}


### Cosmos DB
cosmos_nosql = None
if create_cosmos_db:
    cosmos_account_args = CosmosComponentArgs(
        name=f"{resource_prefix}cosmosacct",
        args={
            "database_account_offer_type": cosmosdb.DatabaseAccountOfferType.STANDARD,
            "locations": [
                cosmosdb.LocationArgs(
                    failover_priority=0,
                    is_zone_redundant=False,
                    location_name="Central US",
                )
            ],
            "backup_policy": cosmosdb.ContinuousModeBackupPolicyArgs(
                continuous_mode_properties=cosmosdb.ContinuousModePropertiesArgs(
                    tier=cosmosdb.ContinuousTier.CONTINUOUS7_DAYS,
                ),
                type="Continuous",
            ),
            "capabilities": [cosmosdb.CapabilityArgs(name="EnableServerless")],
            "capacity": cosmosdb.CapacityArgs(total_throughput_limit=4000),
            "consistency_policy": cosmosdb.ConsistencyPolicyArgs(
                default_consistency_level=cosmosdb.DefaultConsistencyLevel.SESSION,
                max_interval_in_seconds=5,
                max_staleness_prefix=100,
            ),
            "default_identity": "FirstPartyIdentity",
            "enable_free_tier": True,
            "kind": cosmosdb.DatabaseAccountKind.GLOBAL_DOCUMENT_DB,
            "minimal_tls_version": cosmosdb.MinimalTlsVersion.TLS12,
            "public_network_access": cosmosdb.PublicNetworkAccess.ENABLED,
        },
    )

    cosmos_nosql = CosmosNoSQL(
        name=f"{resource_prefix}-cosmos",
        args=CosmosDBArgs(
            resource_group_name=resource_group.name,
            cosmos_account_args=cosmos_account_args,
        ),
        opts=default_opts,
    )

### Create User assigned identity and assign role
assigned_identity = managedidentity.UserAssignedIdentity(
    f"{resource_prefix}-identity",
    location=location,
    resource_group_name=resource_group.name,
    tags={"storageAccount": storage.storage_account.name},
    opts=ResourceOptions(parent=storage.storage_account),
)

roles_assignments = []
if storage_blob_container_args:
    roles_assignments.extend(
        [
            {
                "role_name": "Storage Blob Data Owner",
                "role_id": "b7e6dc6d-f1e8-4753-8033-0f276bb0955b",
                "scope": storage.storage_account.id,
                "name_postfix": "Storage",
            },
            {
                "role_name": "Storage Blob Data Contributor",
                "role_id": "ba92f5b4-2d11-453d-a403-e96b0029c9fe",
                "scope": storage.storage_account.id,
                "name_postfix": "Storage",
            },
            {
                "role_name": "Storage Queue Data Contributor",
                "role_id": "974c5e8b-45b9-4653-ba55-5f855dd0fb88",
                "scope": storage.storage_account.id,
                "name_postfix": "Storage",
            },
        ]
    )
if storage_queue_args:
    roles_assignments.extend(
        [
            {
                "role_name": "Storage Queue Data Contributor",
                "role_id": "974c5e8b-45b9-4653-ba55-5f855dd0fb88",
                "scope": storage.storage_account.id,
                "name_postfix": "Storage",
            },
        ]
    )

for assignment in roles_assignments:
    role_defintion_id = f"/subscription/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/{assignment['role_id']}"
    # Managed Identity
    authorization.RoleAssignment(
        resource_name=f"Managed{assignment['role_name'].replace(' ', '')}{assignment['name_postfix']}",
        scope=assignment["scope"],
        role_definition_id=role_defintion_id,
        principal_id=assigned_identity.principal_id,
        principal_type=authorization.PrincipalType.SERVICE_PRINCIPAL,
        opts=ResourceOptions(parent=assigned_identity),
    )
    # Creator
    authorization.RoleAssignment(
        resource_name=f"User{assignment['role_name'].replace(' ', '')}{assignment['name_postfix']}",
        scope=assignment["scope"],
        role_definition_id=role_defintion_id,
        principal_id=get_client_config().object_id,
        principal_type=authorization.PrincipalType.USER,
        opts=ResourceOptions(parent=storage.storage_account),
    )

export("managed_id", {"client_id": assigned_identity.client_id})

if storage:
    export(
        "storage",
        Output.all(
            name=storage.storage_account.name,
            primary_endpoints=storage.storage_account.primary_endpoints,
            account_keys=storage.storage_account_keys,
            connection_string=storage.storage_connection_string,
            blob_container_endpoints=storage_blob_endpoints,
            queue_endpoints=storage_queue_endpoints,
            sas=storage.storage_sas_urls,
        ).apply(
            lambda args: {
                "account_name": args["name"],
                "account_endpoints": args["primary_endpoints"],
                "account_keys": args["account_keys"],
                "connection_string": args["connection_string"],
                "blob_container_endpoint": args["blob_container_endpoints"],
                "queue_endpoints": args["queue_endpoints"],
                "sas": args["sas"],
            }
        ),
    )

if cosmos_nosql:
    export(
        "cosmosdb",
        Output.all(
            name=cosmos_nosql.cosmos_account.name,
            document_endpoint=cosmos_nosql.cosmos_account.document_endpoint,
            connection_strings=cosmos_nosql.connection_strings,
            primary_master_key=cosmos_nosql.primary_master_key,
            primary_readonly_master_key=cosmos_nosql.primary_readonly_master_key,
        ).apply(
            lambda args: {
                "account_name": args["name"],
                "document_endpoint": args["document_endpoint"],
                "connection_strings": args["connection_strings"],
                "primary_master_key": args["primary_master_key"],
                "primary_readonly_master_key": args[
                    "primary_readonly_master_key"
                ],
            }
        ),
    )
