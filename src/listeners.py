import logging
import threading

from kubernetes import client, watch
from prometheus_client import Gauge, Enum

from src.controller import (
    process_spec,
)
from src.objects import (
    get_locust_object,
    delete_locust_object,
    delete_service,
    delete_replica_set,
    delete_cronjob,
    update_cronjob,
    delete_job,
    create_cronjob,
    create_job,
    create_service,
    create_replica_set,
)

log = logging.getLogger(__name__)


def watch_locust_events(
    group: str,
    version: str,
    namespace: str,
    plural: str,
    gauge: Gauge,
    enum: Enum,
):
    api_client = client.ApiClient()
    custom_api = client.CustomObjectsApi(api_client)
    log.info("Waiting for Locust events to come up...")
    while True:
        stream = watch.Watch().stream(
            custom_api.list_namespaced_custom_object,
            group,
            version,
            namespace,
            plural,
        )
        for event in stream:
            obj = event.get("object")
            operation = event.get("type")
            metadata = obj.get("metadata")
            name = metadata.get("name")
            spec = obj.get("spec")
            if not spec:
                log.warning(f"Locust object {name} does not contain a spec")
                continue
            spec = process_spec(spec)
            log.info(f"Handling {operation} on Locust object {name}")
            if operation == "ADDED":
                gauge.labels(operation=operation, name=name).inc()
                enum.labels(name=name).state("starting")
                if spec["schedule"]:
                    create_cronjob(
                        name,
                        f"cronjob-{name}",
                        f"job-{name}",
                        namespace,
                        spec["workers"],
                        spec["image"],
                        spec["imagePullSecret"],
                        spec["command"],
                        spec["configMapRef"],
                        spec["secretRef"],
                        spec["mountExternalConfig"],
                        spec["mountExternalSecret"],
                        spec["runTime"],
                        spec["schedule"],
                    )
                else:
                    create_job(
                        name,
                        f"job-{name}",
                        namespace,
                        spec["workers"],
                        spec["image"],
                        spec["imagePullSecret"],
                        spec["command"],
                        spec["configMapRef"],
                        spec["secretRef"],
                        spec["mountExternalConfig"],
                        spec["mountExternalSecret"],
                        spec["runTime"],
                    )
                enum.labels(name=name).state("running")
            elif operation == "DELETED":
                enum.labels(name=name).state("stopped")
                gauge.labels(operation=operation, name=name).dec()
                if spec["schedule"]:
                    delete_cronjob(f"cronjob-{name}", namespace)
                else:
                    delete_job(f"job-{name}", namespace)
            elif operation == "MODIFIED":
                if spec["schedule"]:
                    update_cronjob(
                        name,
                        f"cronjob-{name}",
                        f"job-{name}",
                        namespace,
                        spec["workers"],
                        spec["image"],
                        spec["imagePullSecret"],
                        spec["command"],
                        spec["configMapRef"],
                        spec["secretRef"],
                        spec["mountExternalConfig"],
                        spec["mountExternalSecret"],
                        spec["runTime"],
                        spec["schedule"],
                    )


def watch_job_events(
    group: str,
    version: str,
    namespace: str,
    plural: str,
    gauge: Gauge,
    enum: Enum,
):
    api_client = client.BatchV1Api()
    log.info("Waiting for Jobs events to come up...")
    while True:
        for event in watch.Watch().stream(api_client.list_namespaced_job, namespace):
            obj = event.get("object")
            operation = event.get("type")
            job_name: str = obj.metadata.name
            if (
                "locust" not in obj.metadata.labels
                or "issued_by" not in obj.metadata.labels
            ):
                log.info(
                    f"Job object {job_name} does not contain a label locust or issued_by: {obj.metadata.labels}"
                )
                continue
            locust_name: str = obj.metadata.labels.get("locust")
            issued_by: str = obj.metadata.labels.get("issued_by")
            log.info(
                f"Handling {operation} on Job object {job_name} managed by "
                f"Locust {locust_name} and issued by {issued_by}"
            )
            if operation == "ADDED":
                locust_object = get_locust_object(
                    group, version, namespace, plural, locust_name
                )
                if locust_object:
                    gauge.labels(
                        name=locust_name, operation=operation, job_name=job_name
                    ).inc()
                    enum.labels(name=locust_name, job_name=job_name, status="").state(
                        "starting"
                    )
                    spec = process_spec(locust_object["spec"])
                    create_service(
                        locust_name,
                        f"service-{locust_name}",
                        f"job-{locust_name}",
                        namespace,
                    )
                    create_replica_set(
                        locust_name,
                        f"replicaset-{locust_name}",
                        f"service-{locust_name}",
                        namespace,
                        spec["workers"],
                        spec["image"],
                        spec["imagePullSecret"],
                        spec["command"],
                        spec["configMapRef"],
                        spec["secretRef"],
                        spec["mountExternalConfig"],
                        spec["mountExternalSecret"],
                    )
                    enum.labels(name=locust_name, job_name=job_name, status="").state(
                        "running"
                    )
            if (
                operation == "MODIFIED"
                and obj.status.failed == 1
                or obj.status.succeeded == 1
            ):
                if obj.status.succeeded == 1:
                    log.info(f"Job {job_name} finished with status succeeded")
                    enum.labels(
                        name=locust_name, job_name=job_name, status="succeeded"
                    ).state("stopped")
                else:
                    log.info(f"Job {job_name} finished with status failed")
                    enum.labels(
                        name=locust_name, job_name=job_name, status="failed"
                    ).state("stopped")
                if issued_by == "locust":
                    delete_locust_object(
                        group,
                        version,
                        namespace,
                        plural,
                        locust_name,
                    )
                else:
                    delete_job(job_name, namespace)
            if operation == "DELETED":
                gauge.labels(
                    name=locust_name, operation=operation, job_name=job_name
                ).dec()
                delete_replica_set(f"replicaset-{locust_name}", namespace)
                delete_service(f"service-{locust_name}", namespace)


def watch_job_via_thread(
    group: str,
    version: str,
    namespace: str,
    plural: str,
    gauge: Gauge,
    enum: Enum,
):
    t = threading.Thread(
        target=watch_job_events,
        args=(
            group,
            version,
            namespace,
            plural,
            gauge,
            enum,
        ),
    )
    t.daemon = True
    t.start()
