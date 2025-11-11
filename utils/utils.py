import modulepath_fixer  # noqa: F401
from typing import Any, Literal
from configs.generated.servicebus_pkl import servicebus as psb


def load_pkl_config(
    resource_type: Literal["servicebus"],
    pkl_config_file: str,
) -> Any:
    """
    Loads and returns platform configs for the given resource_type.
    Supported types: 'servicebus'.
    """

    # Map resource_type to their loader and platform class
    resource_map = {
        "servicebus": {
            "loader": psb.load_pkl,
            "module": psb,
            "attr": "namespaces",
        },
    }

    if resource_type not in resource_map:
        raise ValueError(f"Unsupported resource type: {resource_type}")

    resource = resource_map[resource_type]
    # psb.load_pkl(pkl_config_file)
    pkl_config = resource["loader"](pkl_config_file)
    # Instantiate the module class and return the relevant attribute
    # psb(pkl_config.namespaces)
    module_instance = resource["module"](getattr(pkl_config, resource["attr"]))
    # module_instance.namespaces
    return getattr(module_instance, resource["attr"])
