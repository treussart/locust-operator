import logging

from kubernetes import client

log = logging.getLogger(__name__)


def process_spec(spec: dict) -> dict:
    if "workers" not in spec:
        spec["workers"] = 1
    if "image" not in spec:
        spec["image"] = "locustio/locust:2.8.5"
    if "imagePullSecret" not in spec:
        spec["imagePullSecret"] = None
    if "command" not in spec:
        spec["command"] = None
    else:
        spec["command"] = spec["command"].split()
    if "configMapRef" not in spec:
        spec["configMapRef"] = None
    if "secretRef" not in spec:
        spec["secretRef"] = None
    if "mountExternalConfig" not in spec:
        spec["mountExternalConfig"] = None
    if "mountExternalSecret" not in spec:
        spec["mountExternalSecret"] = None
    if "runTime" not in spec:
        spec["runTime"] = "5m"
    if "schedule" not in spec:
        spec["schedule"] = ""
    return spec


def check_crd(group: str, version: str, namespace: str, plural: str):
    api_client = client.ApiClient()
    custom_api = client.CustomObjectsApi(api_client)
    try:
        custom_api.list_namespaced_custom_object(group, version, namespace, plural)
    except client.exceptions.ApiException:
        log.critical("Locust CRD not installed")
        exit(1)
