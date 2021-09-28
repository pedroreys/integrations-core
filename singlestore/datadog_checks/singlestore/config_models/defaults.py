# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.fields import get_default_field_value


def shared_global_custom_queries(field, value):
    return get_default_field_value(field, value)


def shared_service(field, value):
    return get_default_field_value(field, value)


def instance_collect_system_metrics(field, value):
    return False


def instance_connect_timeout(field, value):
    return 10


def instance_custom_queries(field, value):
    return get_default_field_value(field, value)


def instance_disable_generic_tags(field, value):
    return False


def instance_empty_default_hostname(field, value):
    return False


def instance_min_collection_interval(field, value):
    return 15


def instance_password(field, value):
    return get_default_field_value(field, value)


def instance_port(field, value):
    return 3306


def instance_read_timeout(field, value):
    return get_default_field_value(field, value)


def instance_service(field, value):
    return get_default_field_value(field, value)


def instance_tags(field, value):
    return get_default_field_value(field, value)


def instance_tls_ca_cert(field, value):
    return get_default_field_value(field, value)


def instance_tls_cert(field, value):
    return get_default_field_value(field, value)


def instance_tls_private_key(field, value):
    return get_default_field_value(field, value)


def instance_tls_private_key_password(field, value):
    return get_default_field_value(field, value)


def instance_tls_validate_hostname(field, value):
    return True


def instance_tls_verify(field, value):
    return True


def instance_use_global_custom_queries(field, value):
    return 'true'


def instance_use_tls(field, value):
    return False


def instance_username(field, value):
    return get_default_field_value(field, value)
