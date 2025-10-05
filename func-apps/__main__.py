# __main__.py
"""
Pulumi program to create Azure App Functions
"""

from typing import Type
import modulepath_fixer  # noqa: F401

from configs import (
    app_svc_plan_name,
    func_app_name,
    location,
    resource_group_prefix,
    subscription_id,
)
from pulumi import export, Output, ResourceOptions
from pulumi_azuread import get_client_config
from pulumi_azure_native import (
    applicationinsights,
    authorization,
    eventgrid,
    managedidentity,
    operationalinsights,
    resources,
    storage,
    web,
)

from modules.storage import (
    StorageChain,
    StorageArgs,
    StorageAccountDefaults,
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
default_tags = {"purpose": "az-204", "app": func_app_name}
resource_prefix = "funcapp"

### Setup Storage
storage_name = f"{resource_prefix}storacct"

storage_account_args = {
    **get_defaults(StorageAccountDefaults),
    "location": location,
    "resource_group_name": resource_group.name,
}

storage_blob_svc_props_args = {
    "blob_services_name": "default",
    "delete_retention_policy": {},
    "resource_group_name": resource_group.name,
}

storage_blob_container_args = {
    "public_access": storage.PublicAccess.NONE,
    "resource_group_name": resource_group.name,
}

storage_queue_args = {"resource_group_name": resource_group.name}

storage = StorageChain(
    name=resource_prefix,
    args=StorageArgs(
        resource_prefix=resource_prefix,
        resource_group_name=resource_group.name,
        storage_account_args=storage_account_args,
        storage_blob_properties_args=storage_blob_svc_props_args,
        storage_blob_container_args=storage_blob_container_args,
        storage_queue_args=storage_queue_args,
        tags=default_tags,
    ),
    opts=default_opts,
)

### Create Log Analytics workspace
log_analytics = operationalinsights.Workspace(
    resource_name=f"{resource_prefix}-workspace",
    location=location,
    resource_group_name=resource_group.name,
    retention_in_days=30,
    sku=operationalinsights.WorkspaceSkuArgs(name="PerGB2018"),
    tags=default_tags,
    opts=default_opts,
)

### Create Application Insights
app_insights = applicationinsights.Component(
    resource_name=f"{resource_prefix}-insights",
    application_type="web",
    disable_local_auth=True,
    kind="web",
    location=location,
    resource_group_name=resource_group.name,
    workspace_resource_id=log_analytics.id,
    tags=default_tags,
    opts=default_opts,
)

### Create Event Grid Topic
event_grid_topic = eventgrid.Topic(
    resource_name=f"{resource_prefix}-event-topic",
    data_residency_boundary=eventgrid.DataResidencyBoundary.WITHIN_REGION,
    input_schema=eventgrid.InputSchema.EVENT_GRID_SCHEMA,
    location=location,
    public_network_access=eventgrid.PublicNetworkAccess.ENABLED,
    minimum_tls_version_allowed=eventgrid.TlsVersion.TLS_VERSION_1_2,
    resource_group_name=resource_group.name,
    tags=default_tags,
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

roles_assignments = [
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
    {
        "role_name": "Storage Table Data Contributor",
        "role_id": "0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3",
        "scope": storage.storage_account.id,
        "name_postfix": "Storage",
    },
    {
        "role_name": "Monitoring Metrics Publisher",
        "role_id": "3913510d-42f4-4e42-8a64-420c390055eb",
        "scope": app_insights.id,
        "name_postfix": "AppInsights" ,
    },
    {
        "role_name": "EventGrid Data Sender",
        "role_id": "d5a91429-5739-47e2-a06b-3470a27159e7",
        "scope": event_grid_topic.id,
        "name_postfix": "EvntGrid",
    },
    {
        "role_name": "EventGrid Data Sender",
        "role_id": "d5a91429-5739-47e2-a06b-3470a27159e7",
        "scope": storage.storage_account.id,
        "name_postfix": "Storage",
    },
]

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

### Create App Service Plan
app_svc_plan = web.AppServicePlan(
    resource_name=app_svc_plan_name,
    location=location,
    kind="functionapp",
    maximum_elastic_worker_count=1,
    reserved=True,
    resource_group_name=resource_group.name,
    sku=web.SkuDescriptionArgs(
        name="FC1", tier="FlexConsumption", size="F1", family="F", capacity=0
    ),
    tags=default_tags,
    zone_redundant=False,
    opts=default_opts,
)

### Create Function App
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
                value=storage.storage_blob_container_url,
            ),
        ),
        runtime=web.FunctionsRuntimeArgs(name="Python", version="3.13"),
        scale_and_concurrency=web.FunctionsScaleAndConcurrencyArgs(
            always_ready=[],
            instance_memory_mb=2048,
            maximum_instance_count=100,
            triggers=None,
        ),
    ),
    identity=web.ManagedServiceIdentityArgs(
        type=web.ManagedServiceIdentityType.USER_ASSIGNED,
        user_assigned_identities=[assigned_identity.id],
    ),
    kind="functionapp",
    location=location,
    resource_group_name=resource_group.name,
    server_farm_id=app_svc_plan.id,
    site_config=web.SiteConfigArgs(
        app_settings=[
            web.NameValuePairArgs(
                name="AzureWebJobsStorage__accountName",
                value=storage.storage_account.name,
            ),
            web.NameValuePairArgs(
                name="AzureWebJobsStorage__credential", value="managedidentity"
            ),
            web.NameValuePairArgs(
                name="AzureWebJobsStorage__clientId",
                value=assigned_identity.client_id,
            ),
            web.NameValuePairArgs(
                name="APPINSIGHTS_INSTRUMENTATIONKEY",
                value=app_insights.instrumentation_key,
            ),
            web.NameValuePairArgs(
                name="APPLICATIONINSIGHTS_AUTHENTICATION_STRING",
                value=Output.concat(
                    "ClientId=",
                    assigned_identity.client_id,
                    ";Authorization=AAD",
                ),
            ),
            web.NameValuePairArgs(
                name="FlashyEventGrid__topicEndpointUri",
                value=event_grid_topic.endpoint,
            ),
            web.NameValuePairArgs(
                name="FlashyEventGrid__credential", value="managedidentity"
            ),
            web.NameValuePairArgs(
                name="FlashyEventGrid__clientId",
                value=assigned_identity.client_id,
            ),
        ],
        cors=web.CorsSettingsArgs(allowed_origins=["https://portal.azure.com"]),
        min_tls_version=web.SupportedTlsVersions.SUPPORTED_TLS_VERSIONS_1_2,
    ),
    tags={
        **default_tags,
        "hidden-link: /app-insights-resource-id": app_insights.id,
    },
    opts=ResourceOptions(parent=app_svc_plan),
)


export("default_host_name", func_app.default_host_name)
export("service_plan_name", app_svc_plan.name)
export("blob_container_url", storage.storage_blob_container_url)
export("connection_string", storage.storage_connection_string)
export("storage_account_keys", storage.storage_account_keys)
export("queue_name", storage.storage_queue.name)
export("eventgrid_topic_endpoint", event_grid_topic.endpoint)
export("manage_user_client_id", assigned_identity.client_id)
