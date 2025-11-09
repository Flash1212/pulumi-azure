from dataclasses import dataclass
from modules.storage import StorageChain
from pulumi import Input, Output, Resource
from typing import Optional

from pulumi_azure_native import (
    applicationinsights,
    authorization,
    operationalinsights,
)


@dataclass
class AnalyticsAndLogsOutputs:
    log_analytics: operationalinsights.Workspace
    app_insights: Optional[applicationinsights.Component] = None


@dataclass
class IdentityOutput:
    principal_id: Input[str]
    parent: Resource
    type: authorization.PrincipalType


@dataclass
class StorageOutputs:
    storage_chain: StorageChain
    storage_blob_endpoints: Optional[dict[str, Output[str]]] = None
    storage_queue_endpoints: Optional[dict[str, Output[str]]] = None
