# Code generated from Pkl module `servicebus`. DO NOT EDIT.
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Set, Union

import pkl


FilterType = Literal["SqlFilter", "CorrelationFilter"]
PublicNetworkAccess = Literal["Enabled", "Disabled", "SecuredByPerimeter"]
SkuName = Literal["Basic", "Standard", "Premium"]
Status = Literal["Active", "Creating", "Deleting", "Disabled", "Restoring", "ReceiveDisabled", "Renaming", "SendDisabled", "Unknown"]

LowerCaseConstraint = str

AuthNameContainsContraint = LowerCaseConstraint
AuthName = AuthNameContainsContraint

NamespaceNameContainsConstraint = LowerCaseConstraint
NamespaceName = NamespaceNameContainsConstraint

TopicNameContainsConstraint = LowerCaseConstraint
TopicName = TopicNameContainsConstraint

SubscriptionNameContainsContraint = LowerCaseConstraint
SubscriptionName = SubscriptionNameContainsContraint

QueueNameContainsContraint = LowerCaseConstraint
QueueName = QueueNameContainsContraint


@dataclass
class RuleSqlFilter:
    compatibilityLevel: Optional[int]

    requiresPreProcessing: Optional[bool]

    sqlExpression: Optional[str]

    _registered_identifier = "servicebus#RuleSqlFilter"


@dataclass
class RuleCorrelationFilter:
    contentType: Optional[str]

    correlationId: Optional[str]

    label: Optional[str]

    messageId: Optional[str]

    properties: Optional[Dict[str, str]]

    replyTo: Optional[str]

    replyToSessionId: Optional[str]

    requiresPreprocessing: Optional[bool]

    sessionId: Optional[str]

    to: Optional[str]

    _registered_identifier = "servicebus#RuleCorrelationFilter"


@dataclass
class RuleAction:
    compatibilityLevel: Optional[int]

    requiresPreProcessing: Optional[bool]

    sqlExpression: Optional[str]

    _registered_identifier = "servicebus#RuleAction"


@dataclass
class SubscriptionRule:
    action: RuleAction

    correlationFilter: RuleCorrelationFilter

    filterType: FilterType

    rule_name: str

    SqlFilter: RuleSqlFilter

    _registered_identifier = "servicebus#SubscriptionRule"


@dataclass
class SubscriptionOptions:
    autoDeleteOnIdle: Optional[str]

    deadLetteringOnFilterEvaluationExceptions: Optional[bool]

    deadLetteringOnMessageExpiration: Optional[bool]

    defaultMessageTtl: Optional[str]

    duplicateDetectionHistoryTimeWindow: Optional[str]

    enabledBatchOperations: Optional[bool]

    forwardDeadLetteredMessagesTo: Optional[str]

    forwardTo: Optional[str]

    isClientAffine: Optional[bool]

    lockDuration: Optional[str]

    maxDeliveryCount: Optional[int]

    requiresSession: Optional[bool]

    status: Status

    _registered_identifier = "servicebus#SubscriptionOptions"


@dataclass
class Subscription:
    name: SubscriptionName

    options: SubscriptionOptions

    rules: List[SubscriptionRule]

    _registered_identifier = "servicebus#Subscription"


@dataclass
class TopicOptions:
    autoDeleteOnIdle: Optional[str]

    defaultMessageTtl: Optional[str]

    duplicateDetectionHistoryTimeWindow: Optional[str]

    enableBatchedOperations: Optional[bool]

    enableExpress: Optional[bool]

    enablePartitioning: Optional[bool]

    maxMessageSizeInKilobytes: Optional[float]

    maxSizeInMegabytes: Optional[int]

    requiresDuplicateDetection: Optional[bool]

    status: Status

    supportOrdering: Optional[bool]

    _registered_identifier = "servicebus#TopicOptions"


@dataclass
class Topic:
    name: TopicName

    options: TopicOptions

    authorizations: Optional[List[AuthorizationRule]]

    subscriptions: List[Subscription]

    _registered_identifier = "servicebus#Topic"


@dataclass
class QueueOptions:
    autoDeleteOnIdle: Optional[str]

    deadLetteringOnMessageExpiration: Optional[bool]

    defaultMessageTtl: Optional[str]

    duplicateDetectionHistoryTimeWindow: Optional[str]

    enableBatchedOperations: Optional[bool]

    enableExpress: Optional[bool]

    enablePartitioning: Optional[bool]

    forwardDeadLetteredMessagesTo: Optional[str]

    forwardTo: Optional[str]

    lockDuration: Optional[str]

    maxDeliveryCount: Optional[int]

    maxMessageSizeInKilobytes: Optional[float]

    maxSizeInMegabytes: Optional[int]

    requiresDuplicateDetection: Optional[bool]

    requiresSession: Optional[bool]

    status: Status

    _registered_identifier = "servicebus#QueueOptions"


@dataclass
class Queue:
    name: QueueName

    options: QueueOptions

    authorizations: Optional[List[AuthorizationRule]]

    _registered_identifier = "servicebus#Queue"


@dataclass
class AuthorizationRule:
    name: AuthName

    listen: bool

    send: bool

    manage: bool

    rights: List[str]

    _registered_identifier = "servicebus#AuthorizationRule"


@dataclass
class Sku:
    name: SkuName

    tier: str

    capacity: Optional[int]

    _registered_identifier = "servicebus#Sku"


@dataclass
class NamespaceOptions:
    alternateName: Optional[str]

    publicNetworkAccess: PublicNetworkAccess

    sku: Sku

    zoneRedundant: Optional[bool]

    _registered_identifier = "servicebus#NamespaceOptions"


@dataclass
class Namespace:
    namePrefix: NamespaceName

    options: NamespaceOptions

    authorizations: Optional[List[AuthorizationRule]]

    queues: Optional[List[Queue]]

    topics: Optional[List[Topic]]

    _registered_identifier = "servicebus#Namespace"


@dataclass
class servicebus:
    namespaces: List[Namespace]

    _registered_identifier = "servicebus"

    @classmethod
    def load_pkl(cls, source):
        # Load the Pkl module at the given source and evaluate it into `servicebus.Module`.
        # - Parameter source: The source of the Pkl module.
        config = pkl.load(source, parser=pkl.Parser(namespace=globals()))
        return config
