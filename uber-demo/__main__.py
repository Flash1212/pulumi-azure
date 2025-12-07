# __main__.py
"""
Pulumi program to create an uber Azure App Function
"""

import modulepath_fixer  # noqa: F401
from typing import Type

from pulumi_configs import (
    app_svc_plan_name,
    create_app_insights,
    create_event_grid,
    create_function_app,
    create_key_vault,
    create_log_analytics,
    create_servicebus,
    create_storage_account,
    blob_names,
    func_app_name,
    func_runtime_args,
    location,
    queue_names,
    resource_group_prefix,
    servicebus_config_file,
    subscription_id,
)
from pulumi import export, Input, Output, ResourceOptions
from pulumi_azuread import get_client_config
from pulumi_azure_native import (
    applicationinsights,
    authorization,
    keyvault,
    eventgrid,
    managedidentity,
    operationalinsights,
    resources,
    storage,
    web,
)

import configs.generated.servicebus_pkl as psb

from utils.module_dataclasses import ServiceBusArgs

from local_dataclasses import (
    AnalyticsAndLogsOutputs,
    IdentityOutput,
    StorageOutputs,
)

from modules.messaging import ServiceBus

from modules.storage import (
    StorageChain,
    StorageArgs,
    StorageAccountDefaults,
    StorageComponentArgs,
)

from utils.utils import load_pkl_config

### Setup Resource Group
resource_group = resources.ResourceGroup(f"{resource_group_prefix}-{location}")
default_opts = ResourceOptions(parent=resource_group)
default_tags = {"purpose": "az-204", "app": func_app_name}
resource_prefix = "funcapp"
identities: list[IdentityOutput] = [
    IdentityOutput(
        principal_id=get_client_config().object_id,
        parent=resource_group,
        type=authorization.PrincipalType.USER,
    )
]


def add_secret(
    secret_name: str,
    secret_value: Input[str],
    key_vault: keyvault.Vault,
    resource_group: resources.ResourceGroup,
):
    secret = keyvault.Secret(
        resource_name=secret_name,
        properties=keyvault.SecretPropertiesArgs(
            value=secret_value,
        ),
        resource_group_name=resource_group.name,
        secret_name=secret_name,
        vault_name=key_vault.name,
        opts=ResourceOptions(parent=key_vault),
    )

    export(
        f"{secret_name}_uri",
        secret.properties.apply(lambda p: p.secret_uri_with_version),
    )
    return secret


def define_akv_permissions() -> dict[str, keyvault.PermissionsArgs]:
    return {
        "admin_permissions": keyvault.PermissionsArgs(
            secrets=[
                "get",
                "list",
                "set",
                "delete",
                "backup",
                "restore",
                "recover",
                "purge",
            ],
            keys=[
                "encrypt",
                "decrypt",
                "wrapKey",
                "unwrapKey",
                "sign",
                "verify",
                "get",
                "list",
                "create",
                "update",
                "import",
                "delete",
                "backup",
                "restore",
                "recover",
                "purge",
            ],
            certificates=[
                "get",
                "list",
                "delete",
                "create",
                "import",
                "update",
                "managecontacts",
                "getissuers",
                "listissuers",
                "setissuers",
                "deleteissuers",
                "manageissuers",
                "recover",
                "purge",
            ],
        ),
        "managed_id_permissions": keyvault.PermissionsArgs(
            secrets=["get"],
            keys=[],
            certificates=[],
        ),
    }


def define_role_assignments(
    app_insights: applicationinsights.Component | None,
    storage_outputs: StorageOutputs | None,
) -> list[dict]:
    role_assignments = []

    if storage_outputs:
        if storage_outputs.storage_blob_endpoints:
            role_assignments.extend(
                [
                    {
                        "role_name": "Storage Blob Data Owner",
                        "role_id": "b7e6dc6d-f1e8-4753-8033-0f276bb0955b",
                        "scope": storage_outputs.storage_chain.storage_account.id,  # noqa: E501
                        "name_postfix": "Storage",
                    },
                    {
                        "role_name": "Storage Blob Data Contributor",
                        "role_id": "ba92f5b4-2d11-453d-a403-e96b0029c9fe",
                        "scope": storage_outputs.storage_chain.storage_account.id,  # noqa: E501
                        "name_postfix": "Storage",
                    },
                ]
            )
        if storage_outputs.storage_queue_endpoints:
            role_assignments.append(
                {
                    "role_name": "Storage Queue Data Contributor",
                    "role_id": "974c5e8b-45b9-4653-ba55-5f855dd0fb88",
                    "scope": storage_outputs.storage_chain.storage_account.id,
                    "name_postfix": "Storage",
                },
            )

    if app_insights:
        role_assignments.append(
            {
                "role_name": "Monitoring Metrics Publisher",
                "role_id": "3913510d-42f4-4e42-8a64-420c390055eb",
                "scope": app_insights.id,
                "name_postfix": "AppInsights",
            },
        )

    return role_assignments


def define_app_settings(
    assigned_identity: managedidentity.UserAssignedIdentity,
    akv_secrets: dict[str, Input[str]] | None,
    storage_outputs: StorageOutputs | None,
    analytics_and_logs: AnalyticsAndLogsOutputs | None,
) -> dict[str, Input[str]]:
    app_settings = {}

    if akv_secrets:
        for secret_name, secret in akv_secrets.items():
            app_settings[secret_name] = secret
    if analytics_and_logs and analytics_and_logs.app_insights:
        app_settings["APPINSIGHTS_INSTRUMENTATIONKEY"] = (
            analytics_and_logs.app_insights.instrumentation_key
        )
        app_settings["APPLICATIONINSIGHTS_AUTHENTICATION_STRING"] = (
            Output.concat(
                "ClientId=",
                assigned_identity.client_id,
                ";Authorization=AAD",
            )
        )
    if storage_outputs:
        app_settings["AzureWebJobsStorage__accountName"] = (
            storage_outputs.storage_chain.storage_account.name
        )
        app_settings["AzureWebJobsStorage__credential"] = "managedidentity"
        app_settings["AzureWebJobsStorage__clientId"] = (
            assigned_identity.client_id
        )

    return app_settings


def setup_anlytics_and_insights(
    create_log_analytics: bool,
    create_app_insights: bool,
    default_opts: ResourceOptions,
    default_tags: dict,
    resource_group_name: Output[str],
    prefix: str,
) -> AnalyticsAndLogsOutputs | None:
    if not create_log_analytics and not create_app_insights:
        return None

    log_analytics = operationalinsights.Workspace(
        resource_name=f"{prefix}-workspace",
        location=location,
        resource_group_name=resource_group_name,
        retention_in_days=30,
        sku=operationalinsights.WorkspaceSkuArgs(name="PerGB2018"),
        tags=default_tags,
        opts=default_opts,
    )

    app_insights = (
        applicationinsights.Component(
            resource_name=f"{prefix}-insights",
            application_type="web",
            disable_local_auth=True,
            kind="web",
            location=location,
            resource_group_name=resource_group_name,
            workspace_resource_id=log_analytics.id,
            tags=default_tags,
            opts=default_opts,
        )
        if create_app_insights
        else None
    )
    return AnalyticsAndLogsOutputs(
        log_analytics=log_analytics, app_insights=app_insights
    )


def setup_akv(
    create: bool,
    default_opts: ResourceOptions,
    default_tags: dict,
    identities: list[IdentityOutput],
    location: str,
    resource_group_name: Output[str],
    prefix: str,
) -> keyvault.Vault | None:
    if not create:
        return None

    permissions = define_akv_permissions()
    access_policies: list[keyvault.AccessPolicyEntryArgs] = []

    identities_and_permissions: dict[Input[str], keyvault.PermissionsArgs] = {}

    for identity in identities:
        permission = permissions["managed_id_permissions"]
        if identity.type == authorization.PrincipalType.USER:
            permission = permissions["admin_permissions"]

        identities_and_permissions[identity.principal_id] = permission

    for identity, permissions in identities_and_permissions.items():
        access_policies.append(
            keyvault.AccessPolicyEntryArgs(
                object_id=identity,
                permissions=permissions,
                tenant_id=get_client_config().tenant_id,
            )
        )

    key_vault = keyvault.Vault(
        resource_name=f"{prefix}-keyvault",
        location=location,
        properties=keyvault.VaultPropertiesArgs(
            access_policies=access_policies,
            enable_rbac_authorization=False,
            enabled_for_deployment=True,
            enabled_for_disk_encryption=True,
            enabled_for_template_deployment=True,
            sku=keyvault.SkuArgs(name=keyvault.SkuName.STANDARD, family="A"),
            enable_soft_delete=False,
            tenant_id=get_client_config().tenant_id,
        ),
        resource_group_name=resource_group_name,
        tags=default_tags,
        opts=default_opts,
    )

    export("azure_key_vault_uri", key_vault.properties.vault_uri)

    return key_vault


def setup_assigned_identity(
    default_opts: ResourceOptions,
    default_tags: dict,
    location: str,
    prefix: str,
    resource_group_name: Output[str],
) -> managedidentity.UserAssignedIdentity:
    assigned_identity = managedidentity.UserAssignedIdentity(
        f"{prefix}-identity",
        location=location,
        resource_group_name=resource_group_name,
        tags=default_tags,
        opts=default_opts,
    )

    export("managed_user_client_id", assigned_identity.client_id)
    return assigned_identity


def setup_event_grid(
    create_event_grid: bool,
    default_opts: ResourceOptions,
    default_tags: dict,
    location: str,
    resource_group_name: Output[str],
    prefix: str,
) -> eventgrid.SystemTopic | None:
    if not create_event_grid:
        return None

    event_grid_topic = eventgrid.SystemTopic(
        resource_name=f"{prefix}-event-topic",
        location=location,
        resource_group_name=resource_group_name,
        tags=default_tags,
        opts=default_opts,
    )

    return event_grid_topic


def setup_roles(
    name: str,
    identities: list[IdentityOutput],
    role_id: str,
    subscription_id: str,
    scope: str,
):
    role_definition_id = (
        f"/subscription/{subscription_id}/providers/Microsoft.Authorization/"
        f"roleDefinitions/{role_id}"
    )

    resource_name = name
    for i, identity in enumerate(identities):
        if identity.type == authorization.PrincipalType.SERVICE_PRINCIPAL:
            resource_name = f"Managed{name}-{i}"
        if identity.type == authorization.PrincipalType.USER:
            resource_name = f"User{name}-{i}"

        authorization.RoleAssignment(
            resource_name=resource_name,
            principal_id=identity.principal_id,
            principal_type=identity.type,
            role_definition_id=role_definition_id,
            scope=scope,
            opts=ResourceOptions(parent=identity.parent),
        )


def setup_servicebus(
    create_servicebus: bool,
    default_opts: ResourceOptions,
    default_tags: dict,
    prefix: str,
    resource_group_name: Output[str],
) -> ServiceBus | None:
    if not create_servicebus:
        return None

    servicebus_configs: list[psb.Namespace] = load_pkl_config(
        resource_type="servicebus", pkl_config_file=servicebus_config_file
    )

    sbs = ServiceBus(
        name=prefix,
        args=ServiceBusArgs(
            location=location,
            resource_group_name=resource_group_name,
            pkl_configs=servicebus_configs,
            tags=default_tags,
        ),
        opts=default_opts,
    )

    export("servicebus_secrets", sbs.servicebus_secrets)

    return sbs


def setup_storage(
    create: bool,
    default_opts: ResourceOptions,
    default_tags: dict,
    resource_group_name: Output[str],
    prefix: str,
) -> StorageOutputs | None:
    if not create:
        return None

    def get_defaults(
        storage_defaults_class: Type[StorageAccountDefaults],
    ) -> dict:
        return {
            k: v
            for k, v in vars(storage_defaults_class).items()
            if not k.startswith("__") and not callable(v)
        }

    storage_account_args = StorageComponentArgs(
        name=f"{prefix}storacct",
        args={
            **get_defaults(StorageAccountDefaults),
            "location": location,
            "resource_group_name": resource_group.name,
        },
    )

    storage_blob_svc_props_args = StorageComponentArgs(
        name=f"{prefix}-blob-props",
        args={
            "blob_services_name": "default",
            "delete_retention_policy": {},
            "resource_group_name": resource_group.name,
        },
    )

    if create_function_app:
        blob_names.append(prefix)

    storage_blob_container_args = [
        StorageComponentArgs(
            name=name,
            args={
                "public_access": storage.PublicAccess.NONE,
                "resource_group_name": resource_group.name,
            },
        )
        for name in blob_names
    ]

    storage_queue_args = [
        StorageComponentArgs(
            name=name,
            args={"resource_group_name": resource_group.name},
        )
        for name in queue_names
    ]

    storage_chain = StorageChain(
        name=prefix,
        args=StorageArgs(
            resource_group_name=resource_group_name,
            storage_account_args=storage_account_args,
            storage_blob_properties_args=storage_blob_svc_props_args,
            storage_blob_container_args=storage_blob_container_args,
            storage_queue_args=storage_queue_args,
            tags=default_tags,
        ),
        opts=default_opts,
    )

    storage_blob_endpoints = {
        name: Output.concat(
            storage_chain.storage_account.primary_endpoints.blob,
            container.name,
        )
        for name, container in storage_chain.storage_blob_containers.items()
    }
    storage_queue_endpoints = {
        name: Output.concat(
            storage_chain.storage_account.primary_endpoints.queue,
            queue.name,
        )
        for name, queue in storage_chain.storage_queues.items()
    }
    export("blob_container_endpoints", storage_blob_endpoints)
    export("storage_secrets", storage_chain.storage_secrets)
    export("storage_account_keys", storage_chain.storage_account_keys)
    export("queue_names", storage_chain.storage_queues.keys())

    return StorageOutputs(
        storage_chain=storage_chain,
        storage_blob_endpoints=storage_blob_endpoints,
        storage_queue_endpoints=storage_queue_endpoints,
    )


def setup_web_app(
    app_insights: applicationinsights.Component | None,
    app_svc_plan_name: str,
    create: bool | None,
    default_opts: ResourceOptions,
    default_tags: dict,
    func_app_name: str,
    assigned_identity: managedidentity.UserAssignedIdentity,
    func_runtime_args: dict | None,
    storage_outputs: StorageOutputs | None,
    location: str,
    resource_group_name: Output[str],
) -> web.WebApp | None:
    if not create:
        return None

    app_svc_plan = web.AppServicePlan(
        resource_name=app_svc_plan_name,
        location=location,
        kind="functionapp",
        maximum_elastic_worker_count=1,
        reserved=True,
        resource_group_name=resource_group_name,
        sku=web.SkuDescriptionArgs(
            name="FC1",
            tier="FlexConsumption",
            size="F1",
            family="F",
            capacity=0,
        ),
        tags=default_tags,
        zone_redundant=False,
        opts=default_opts,
    )
    export("service_plan_name", app_svc_plan.name)

    funcs_deployment_storage_args_value = None
    if storage_outputs and storage_outputs.storage_blob_endpoints:
        funcs_deployment_storage_args_value = (
            storage_outputs.storage_blob_endpoints[resource_prefix]
        )

    web_func_runtime_args = web.FunctionsRuntimeArgs(
        name="Python", version="3.13"
    )

    if func_runtime_args:
        web_func_runtime_args = web.FunctionsRuntimeArgs(**func_runtime_args)

    func_app_tags = default_tags.copy()
    if app_insights:
        func_app_tags = app_insights.id.apply(
            lambda id: {
                **default_tags,
                "hidden-link: /app-insights-resource-id": id,
            }
        )

    func_app = web.WebApp(
        resource_name=func_app_name,
        function_app_config=web.FunctionAppConfigArgs(
            deployment=web.FunctionsDeploymentArgs(
                storage=web.FunctionsDeploymentStorageArgs(
                    authentication=web.FunctionsDeploymentAuthenticationArgs(
                        user_assigned_identity_resource_id=assigned_identity.id,
                        type=web.AuthenticationType.USER_ASSIGNED_IDENTITY,
                    ),
                    type=web.FunctionsDeploymentStorageType.BLOB_CONTAINER,
                    value=funcs_deployment_storage_args_value,
                ),
            ),
            runtime=web_func_runtime_args,
            scale_and_concurrency=web.FunctionsScaleAndConcurrencyArgs(
                always_ready=[],
                instance_memory_mb=2048,
                maximum_instance_count=100,
                triggers=None,
            ),
        ),
        identity=web.ManagedServiceIdentityArgs(
            type=web.ManagedServiceIdentityType.SYSTEM_ASSIGNED_USER_ASSIGNED,
            user_assigned_identities=[assigned_identity.id],
        ),
        kind="functionapp",
        location=location,
        resource_group_name=resource_group.name,
        server_farm_id=app_svc_plan.id,
        site_config=web.SiteConfigArgs(
            # app_settings will be managed separately
            cors=web.CorsSettingsArgs(
                allowed_origins=["https://portal.azure.com"]
            ),
            min_tls_version=web.SupportedTlsVersions.SUPPORTED_TLS_VERSIONS_1_2,
        ),
        tags=func_app_tags,
        opts=ResourceOptions(
            parent=app_svc_plan, ignore_changes=["siteConfig.appettings"]
        ),
    )
    export("default_host_name", func_app.default_host_name)

    return func_app


def setup_web_app_settings(
    func_app: web.WebApp,
    resource_group_name: Output[str],
    app_settings: dict[str, Input[str]],
) -> web.WebAppApplicationSettings:
    return web.WebAppApplicationSettings(
        resource_name="webappsettings",
        name=func_app.name,
        resource_group_name=resource_group_name,
        properties=app_settings,
        opts=ResourceOptions(parent=func_app),
    )


storage_outputs = setup_storage(
    create=create_storage_account,
    default_opts=default_opts,
    default_tags=default_tags,
    resource_group_name=resource_group.name,
    prefix=resource_prefix,
)

servicebus_outputs = setup_servicebus(
    create_servicebus=create_servicebus,
    default_opts=default_opts,
    default_tags=default_tags,
    prefix=resource_prefix,
    resource_group_name=resource_group.name,
)

event_grid_topic = setup_event_grid(
    create_event_grid=create_event_grid,
    default_opts=default_opts,
    default_tags=default_tags,
    location=location,
    resource_group_name=resource_group.name,
    prefix=resource_prefix,
)

assigned_identity = setup_assigned_identity(
    default_opts=default_opts,
    default_tags=default_tags,
    location=location,
    prefix=resource_prefix,
    resource_group_name=resource_group.name,
)

identities.append(
    IdentityOutput(
        principal_id=assigned_identity.principal_id,
        parent=assigned_identity,
        type=authorization.PrincipalType.SERVICE_PRINCIPAL,
    ),
)

analytics_and_logs = setup_anlytics_and_insights(
    create_log_analytics=create_log_analytics,
    create_app_insights=create_app_insights,
    default_opts=default_opts,
    default_tags=default_tags,
    resource_group_name=resource_group.name,
    prefix=resource_prefix,
)

func_app = setup_web_app(
    app_insights=analytics_and_logs.app_insights
    if analytics_and_logs
    else None,
    app_svc_plan_name=app_svc_plan_name,
    assigned_identity=assigned_identity,
    create=(storage_outputs and create_function_app),
    default_opts=default_opts,
    default_tags=default_tags,
    func_app_name=func_app_name,
    func_runtime_args=func_runtime_args,
    location=location,
    resource_group_name=resource_group.name,
    storage_outputs=storage_outputs,
)

role_assignments = define_role_assignments(
    app_insights=analytics_and_logs.app_insights
    if analytics_and_logs and analytics_and_logs.app_insights
    else None,
    storage_outputs=storage_outputs if storage_outputs else None,
)


if func_app and func_app.identity:
    identities.append(
        IdentityOutput(
            principal_id=func_app.identity.apply(
                lambda id: id.principal_id if id else ""
            ),
            parent=func_app,
            type=authorization.PrincipalType.SERVICE_PRINCIPAL,
        )
    )
for assignment in role_assignments:
    name = (
        f"{assignment['role_name'].replace(' ', '')}"
        f"{assignment['name_postfix']}"
    )
    setup_roles(
        name=name,
        identities=identities,
        role_id=assignment["role_id"],
        subscription_id=subscription_id,
        scope=assignment["scope"],
    )

key_vault = setup_akv(
    create=create_key_vault,
    default_opts=default_opts,
    default_tags=default_tags,
    identities=identities,
    location=location,
    resource_group_name=resource_group.name,
    prefix=resource_prefix,
)

app_settings_secrets: dict[str, Input[str]] = {}
secrets_dict: dict[str, Input[str]] = {}

if storage_outputs and storage_outputs.storage_chain:
    secrets_dict.update(storage_outputs.storage_chain.storage_secrets.secrets)

if servicebus_outputs and servicebus_outputs.servicebus_secrets:
    secrets_dict.update(servicebus_outputs.servicebus_secrets.secrets)

if key_vault:
    for secret_name, secret_value in secrets_dict.items():
        secret = add_secret(
            key_vault=key_vault,
            resource_group=resource_group,
            secret_name=secret_name,
            secret_value=secret_value,
        )
        if "StorageConnectionString" in secret_name:
            app_settings_secrets[secret_name] = Output.concat(
                "@Microsoft.KeyVault(SecretUri=",
                secret.properties.apply(lambda p: p.secret_uri_with_version),
                ")",
            )
        if "ConnectionStringSecondary" in secret_name:
            app_settings_secrets[secret_name] = Output.concat(
                "@Microsoft.KeyVault(SecretUri=",
                secret.properties.apply(lambda p: p.secret_uri_with_version),
                ")",
            )


if func_app:
    app_settings = define_app_settings(
        akv_secrets=app_settings_secrets,
        storage_outputs=storage_outputs,
        analytics_and_logs=analytics_and_logs,
        assigned_identity=assigned_identity,
    )

    web_app_settings = setup_web_app_settings(
        func_app=func_app,
        resource_group_name=resource_group.name,
        app_settings=app_settings,
    )

    export("web_app_settings", app_settings)
