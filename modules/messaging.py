from typing import Optional

import pulumi_azure_native.servicebus as asb
from pulumi import (
    ComponentResource,
    Output,
    ResourceOptions,
)

import configs.generated.servicebus_pkl as psb
from utils.module_dataclasses import SecretsObject, ServiceBusArgs


class ServiceBus(ComponentResource):
    def __init__(
        self,
        name: str,
        args: ServiceBusArgs,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        """
        Init creates a new Azure Service Bus based on pkl configuration file.

        Args:
            name (str): The name of the Pulumi component.
            args (ServiceBusArgs): The configuration for the Service Bus
                Namespace.
            opts (Optional[ResourceOptions], optional): The resource options for
                the component. Defaults to None.

        Returns:
            None
        """
        super().__init__(
            "caregility:sbs:ServiceBus",
            name,
            None,
            opts,
            False,
            None,
        )

        self.primary_conn_strings: list[SecretsObject] = []
        self.resource_group_name = args.resource_group_name
        self.tags = args.tags
        conn_str_suffix = "-conn-str"

        for namespace in args.pkl_configs:
            svc_bus = asb.Namespace(
                resource_name=namespace.namePrefix,
                args=asb.NamespaceArgs(
                    alternate_name=namespace.options.alternateName,
                    location=args.location,
                    namespace_name=namespace.namePrefix,
                    public_network_access=namespace.options.publicNetworkAccess,
                    resource_group_name=self.resource_group_name,
                    sku=asb.SBSkuArgs(
                        name=asb.SkuName(namespace.options.sku.name),
                        tier=asb.SkuTier(namespace.options.sku.tier),
                    ),
                    tags=args.tags,
                    zone_redundant=namespace.options.zoneRedundant,
                ),
                opts=ResourceOptions(
                    parent=self,
                    ignore_changes=["privateEndpointConnections"],
                ),
            )
            if namespace.authorizations:
                for auth in namespace.authorizations:
                    self.__create_authorization_rule(
                        name=auth.name,
                        namespace_name=svc_bus.name,
                        rights=auth.rights,
                        parent=svc_bus,
                        secret_name=f"{auth.name}{conn_str_suffix}",
                    )

            if namespace.topics:
                for topic in namespace.topics:
                    tp = self.__create_topic(topic=topic, parent=svc_bus)
                    if topic.authorizations:
                        for auth in topic.authorizations:
                            self.__create_authorization_rule(
                                name=auth.name,
                                namespace_name=svc_bus.name,
                                rights=auth.rights,
                                parent=tp,
                                secret_name=f"{auth.name}{conn_str_suffix}",
                            )
                    if topic.subscriptions:
                        for subscription in topic.subscriptions:
                            sub = self.__create_subscription(
                                namespace=svc_bus,
                                subscription=subscription,
                                parent=tp,
                            )
                            if subscription.rules:
                                for rule in subscription.rules:
                                    self.__create_subscription_rule(
                                        namespace_name=svc_bus.name,
                                        rule=rule,
                                        parent=sub,
                                        subscription_name=sub.name,
                                        topic_name=tp.name,
                                    )

            if namespace.queues:
                for queue in namespace.queues:
                    sbq = self.__create_queue(queue=queue, parent=svc_bus)
                    if queue.authorizations:
                        for auth in queue.authorizations:
                            self.__create_authorization_rule(
                                name=auth.name,
                                namespace_name=svc_bus.name,
                                rights=auth.rights,
                                parent=sbq,
                                secret_name=f"{auth.name}{conn_str_suffix}",
                            )

        self.register_outputs({})

    def __create_topic(
        self, topic: psb.Topic, parent: asb.Namespace
    ) -> asb.Topic:
        """
        Private method to create a new Azure Service Bus Topic from
        Pkl configuration into previously created servicebus namespace.

        Args:
            topic (pkl_sbs.Topic): The Pkl configuration for the topic.
            parent (Namespace): The parent namespace resource.

        Returns:
            Topic: The Azure Service Bus Topic resource.
        """
        return asb.Topic(
            f"{topic.name}-topic",
            asb.TopicArgs(
                namespace_name=parent.name,
                resource_group_name=self.resource_group_name,
                topic_name=topic.name,
                auto_delete_on_idle=topic.options.autoDeleteOnIdle,
                default_message_time_to_live=topic.options.defaultMessageTtl,
                duplicate_detection_history_time_window=topic.options.duplicateDetectionHistoryTimeWindow,
                enable_batched_operations=topic.options.enableBatchedOperations,
                enable_express=topic.options.enableExpress,
                enable_partitioning=topic.options.enablePartitioning,
                max_size_in_megabytes=topic.options.maxSizeInMegabytes,
                requires_duplicate_detection=topic.options.requiresDuplicateDetection,
                status=asb.EntityStatus(topic.options.status),
                support_ordering=topic.options.supportOrdering,
            ),
            opts=ResourceOptions(parent=parent),
        )

    def __create_queue(
        self, queue: psb.Queue, parent: asb.Namespace
    ) -> asb.Queue:
        """
        Private method to create a new Azure Service Bus Queue from
        Pkl configuration into previously created servicebus namespace.

        Args:
            queue (pkl_sbs.Queue): The Pkl configuration for the queue.
            parent (Namespace): The parent namespace resource.

        Returns:
            Queue: The Azure Service Bus Queue resource.
        """
        return asb.Queue(
            f"{queue.name}-queue",
            asb.QueueArgs(
                namespace_name=parent.name,
                resource_group_name=self.resource_group_name,
                queue_name=queue.name,
                auto_delete_on_idle=queue.options.autoDeleteOnIdle,
                dead_lettering_on_message_expiration=queue.options.deadLetteringOnMessageExpiration,
                default_message_time_to_live=queue.options.defaultMessageTtl,
                duplicate_detection_history_time_window=queue.options.duplicateDetectionHistoryTimeWindow,
                enable_batched_operations=queue.options.enableBatchedOperations,
                enable_express=queue.options.enableExpress,
                enable_partitioning=queue.options.enablePartitioning,
                forward_dead_lettered_messages_to=queue.options.forwardDeadLetteredMessagesTo,
                forward_to=queue.options.forwardTo,
                lock_duration=queue.options.lockDuration,
                max_delivery_count=queue.options.maxDeliveryCount,
                max_message_size_in_kilobytes=queue.options.maxMessageSizeInKilobytes,
                max_size_in_megabytes=queue.options.maxSizeInMegabytes,
                requires_duplicate_detection=queue.options.requiresDuplicateDetection,
                requires_session=queue.options.requiresSession,
                status=asb.EntityStatus(queue.options.status),
            ),
            opts=ResourceOptions(parent=parent),
        )

    def __create_subscription(
        self,
        namespace: asb.Namespace,
        subscription: psb.Subscription,
        parent: asb.Topic,
    ) -> asb.Subscription:
        """
        Private method to create a new Azure Service Bus Subscription from
        Pkl configuration into previously created servicebus topic.

        Args:
            topic_name (str): The name of the topic the subscription is
                associated with.
            subscription (pkl_sbs.Subscription): The Pkl configuration for
                the subscription.
            parent (Topic): The parent topic resource.

        Returns:
            Subscription: The Azure Service Bus Subscription
            resource.
        """
        return asb.Subscription(
            f"{subscription.name}-sub",
            asb.SubscriptionArgs(
                namespace_name=namespace.name,
                resource_group_name=self.resource_group_name,
                subscription_name=subscription.name,
                topic_name=parent.name,
                auto_delete_on_idle=subscription.options.autoDeleteOnIdle,
                dead_lettering_on_filter_evaluation_exceptions=subscription.options.deadLetteringOnFilterEvaluationExceptions,
                dead_lettering_on_message_expiration=subscription.options.deadLetteringOnMessageExpiration,
                default_message_time_to_live=subscription.options.defaultMessageTtl,
                duplicate_detection_history_time_window=subscription.options.duplicateDetectionHistoryTimeWindow,
                enable_batched_operations=subscription.options.enabledBatchOperations,
                forward_dead_lettered_messages_to=subscription.options.forwardDeadLetteredMessagesTo,
                forward_to=subscription.options.forwardTo,
                is_client_affine=subscription.options.isClientAffine,
                lock_duration=subscription.options.lockDuration,
                max_delivery_count=subscription.options.maxDeliveryCount,
                requires_session=subscription.options.requiresSession,
                status=asb.EntityStatus(subscription.options.status),
            ),
            opts=ResourceOptions(parent=parent),
        )

    def __create_subscription_rule(
        self,
        namespace_name: Output[str],
        rule: psb.SubscriptionRule,
        parent: asb.Subscription,
        subscription_name: Output[str],
        topic_name: Output[str],
    ):
        action_args = None
        if rule.action:
            action_args = asb.ActionArgs(
                compatibility_level=rule.action.compatibilityLevel,
                requires_preprocessing=rule.action.requiresPreprocessing,
                sql_expression=rule.action.sqlExpression,
            )
        correlation_filter_args = None
        if rule.correlationFilter:
            correlation_filter_args = asb.CorrelationFilterArgs(
                correlation_id=rule.correlationFilter.correlationId,
                content_type=rule.correlationFilter.contentType,
                label=rule.correlationFilter.label,
                message_id=rule.correlationFilter.messageId,
                properties=rule.correlationFilter.properties,
                reply_to=rule.correlationFilter.replyTo,
                reply_to_session_id=rule.correlationFilter.replyToSessionId,
                requires_preprocessing=rule.correlationFilter.requiresPreprocessing,
                session_id=rule.correlationFilter.sessionId,
                to=rule.correlationFilter.to,
            )
        sql_filter_args = None
        if rule.sqlFilter:
            sql_filter_args = asb.SqlFilterArgs(
                compatibility_level=rule.sqlFilter.compatibilityLevel,
                requires_preprocessing=rule.sqlFilter.requiresPreprocessing,
                sql_expression=rule.sqlFilter.sqlExpression,
            )

        return asb.Rule(
            f"{rule.rule_name}-rule",
            namespace_name=namespace_name,
            resource_group_name=self.resource_group_name,
            subscription_name=subscription_name,
            topic_name=topic_name,
            action=action_args,
            correlation_filter=correlation_filter_args,
            filter_type=asb.FilterType(rule.filterType),
            rule_name=rule.rule_name,
            sql_filter=sql_filter_args,
            opts=ResourceOptions(parent=parent),
        )

    def __create_authorization_rule(
        self,
        name: str,
        namespace_name: Output[str],
        parent: asb.Queue | asb.Topic | asb.Namespace,
        rights: list[str],
        secret_name: str,
    ) -> None:
        """
        Private method to create a new Azure Service Bus Authorization Rule
        from Pkl configuration into previously created servicebus queue or
        topic.

        Args:
            name (str): The name of the authorization rule.
            rights (list[str]): The rights for the authorization rule.
            parent (Queue | Topic): The parent queue
                or topic resource.

        Returns:
            TopicAuthorizationRule |
            QueueAuthorizationRule:
            The Azure Service Bus Authorization Rule resource.
        """
        if isinstance(parent, asb.Queue):
            rule = asb.QueueAuthorizationRule(
                f"{name}-auth",
                asb.QueueAuthorizationRuleArgs(
                    namespace_name=namespace_name,
                    resource_group_name=self.resource_group_name,
                    queue_name=parent.name,
                    authorization_rule_name=name,
                    rights=[asb.AccessRights(right) for right in rights],
                ),
                opts=ResourceOptions(parent=parent),
            )

            keys = asb.list_queue_keys_output(
                authorization_rule_name=rule.name,
                namespace_name=namespace_name,
                queue_name=parent.name,
                resource_group_name=self.resource_group_name,
            )
        elif isinstance(parent, asb.Topic):
            rule = asb.TopicAuthorizationRule(
                f"{name}-auth",
                asb.TopicAuthorizationRuleArgs(
                    namespace_name=namespace_name,
                    resource_group_name=self.resource_group_name,
                    topic_name=parent.name,
                    authorization_rule_name=name,
                    rights=[asb.AccessRights(right) for right in rights],
                ),
                opts=ResourceOptions(parent=parent),
            )
            keys = asb.list_topic_keys_output(
                authorization_rule_name=rule.name,
                topic_name=parent.name,
                namespace_name=namespace_name,
                resource_group_name=self.resource_group_name,
            )
        elif isinstance(parent, asb.Namespace):
            rule = asb.NamespaceAuthorizationRule(
                f"{name}-auth",
                asb.NamespaceAuthorizationRuleArgs(
                    namespace_name=namespace_name,
                    resource_group_name=self.resource_group_name,
                    authorization_rule_name=name,
                    rights=[asb.AccessRights(right) for right in rights],
                ),
                opts=ResourceOptions(parent=parent),
            )
            keys = asb.list_namespace_keys_output(
                authorization_rule_name=rule.name,
                namespace_name=namespace_name,
                resource_group_name=self.resource_group_name,
            )
        self.primary_conn_strings.append(
            SecretsObject(
                secrets={
                    secret_name: Output.secret(
                        keys.apply(lambda k: k.primary_connection_string)
                    )
                },
                origin="automation",
                purpose="connection-strings",
            )
        )
