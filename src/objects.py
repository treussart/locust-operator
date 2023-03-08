import logging
from datetime import timedelta

from durationpy import from_str
from kubernetes import client

from src.constants import ADDITIONAL_ACTIVE_DEADLINE_MINUTES

log = logging.getLogger(__name__)


def get_seconds(run_time: str) -> int:
    return (
        from_str(run_time) + timedelta(minutes=ADDITIONAL_ACTIVE_DEADLINE_MINUTES)
    ).seconds


def get_image_pull_secret(image_pull_secret: str):
    if image_pull_secret:
        return [client.V1LocalObjectReference(name=image_pull_secret)]


def get_command_master(workers: int):
    return [
        "--master",
        "--headless",
        f"--expect-workers={workers}",
    ]


def get_command_worker(name: str):
    return [
        "--worker",
        "--headless",
        f"--master-host={name}",
    ]


def get_env_from(secret: str, configmap: str):
    env_from = []
    if secret:
        env_from.append(
            client.V1EnvFromSource(
                secret_ref=client.V1SecretEnvSource(name=secret),
            )
        )
    if configmap:
        env_from.append(
            client.V1EnvFromSource(
                config_map_ref=client.V1ConfigMapEnvSource(name=configmap),
            )
        )
    return env_from


def get_volumes(
    mount_external_config: dict, mount_external_secret: dict
) -> [dict, dict]:
    volume_mounts = []
    volumes = []
    if mount_external_config:
        volumes.append(
            client.V1Volume(
                name=mount_external_config["name"],
                config_map=client.V1ConfigMapVolumeSource(
                    name=mount_external_config["name"]
                ),
            )
        )
        volume_mounts.append(
            client.V1VolumeMount(
                mount_path=mount_external_config["mountPath"],
                name=mount_external_config["name"],
                read_only=True,
            )
        )
    if mount_external_secret:
        volumes.append(
            client.V1Volume(
                name=mount_external_secret["name"],
                secret=client.V1SecretVolumeSource(
                    secret_name=mount_external_secret["name"]
                ),
            )
        )
        volume_mounts.append(
            client.V1VolumeMount(
                mount_path=mount_external_secret["mountPath"],
                name=mount_external_secret["name"],
                read_only=True,
            )
        )
    return volumes, volume_mounts


def create_service(name, service_name, job_name, namespace):
    try:
        api_instance = client.CoreV1Api()
        body = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(name=service_name, labels={"locust": name}),
            spec=client.V1ServiceSpec(
                selector={"app": job_name, "locust": name},
                ports=[
                    client.V1ServicePort(
                        name="master", protocol="TCP", port=5557, target_port=5557
                    ),
                    client.V1ServicePort(
                        name="metrics", protocol="TCP", port=8089, target_port=8089
                    ),
                ],
            ),
        )
        api_instance.create_namespaced_service(namespace=namespace, body=body)
        log.info(f"Service created for {service_name}")
    except client.exceptions.ApiException:
        log.info(f"Create service {service_name} exception")
        if log.getEffectiveLevel() == logging.DEBUG:
            log.exception(f"Create service {service_name} exception")
    except Exception:
        log.exception(f"Create service {service_name} exception")


def delete_service(service_name: str, namespace: str):
    try:
        api_instance = client.CoreV1Api()
        api_instance.delete_namespaced_service(
            name=service_name,
            namespace=namespace,
            body=client.V1DeleteOptions(
                propagation_policy="Foreground", grace_period_seconds=0
            ),
        )
        log.info(f"Service deleted for {service_name}")
    except client.exceptions.ApiException:
        log.info(f"Delete service {service_name} exception")
        if log.getEffectiveLevel() == logging.DEBUG:
            log.exception(f"Delete service {service_name} exception")
    except Exception:
        log.exception(f"Delete service {service_name} exception")


def create_job(
    name: str,
    job_name: str,
    namespace: str,
    workers: int,
    image: str,
    image_pull_secret: str,
    command: str,
    configmap: str,
    secret: str,
    mount_external_config: dict,
    mount_external_secret: dict,
    run_time: str,
):
    try:
        volumes, volume_mounts = get_volumes(
            mount_external_config, mount_external_secret
        )
        container = client.V1Container(
            name="locust",
            image=image,
            command=command,
            args=get_command_master(workers),
            ports=[
                client.V1ContainerPort(
                    host_port=5557, container_port=5557, name="master"
                ),
                client.V1ContainerPort(
                    host_port=8089, container_port=8089, name="metrics"
                ),
            ],
            env_from=get_env_from(secret, configmap),
            env=[client.V1EnvVar(name="LOCUST_RUN_TIME", value=run_time)],
            volume_mounts=volume_mounts,
        )
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(
                name=job_name, labels={"app": job_name, "locust": name}
            ),
            spec=client.V1PodSpec(
                restart_policy="Never",
                containers=[container],
                volumes=volumes,
                image_pull_secrets=get_image_pull_secret(image_pull_secret),
            ),
        )
        spec = client.V1JobSpec(
            template=template,
            backoff_limit=0,
            completions=1,
            parallelism=1,
            active_deadline_seconds=get_seconds(run_time),
        )
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=job_name, labels={"locust": name, "issued_by": "locust"}
            ),
            spec=spec,
        )
        api_instance = client.BatchV1Api()
        api_instance.create_namespaced_job(body=job, namespace=namespace)
        log.info(f"Job created for {job_name}")
    except client.exceptions.ApiException:
        log.info(f"Create job {job_name} exception")
        if log.getEffectiveLevel() == logging.DEBUG:
            log.exception(f"Create job {job_name} exception")
    except Exception:
        log.exception(f"Create job {job_name} exception")


def delete_job(job_name: str, namespace: str):
    try:
        api_instance = client.BatchV1Api()
        api_instance.delete_namespaced_job(
            name=job_name,
            namespace=namespace,
            body=client.V1DeleteOptions(
                propagation_policy="Foreground", grace_period_seconds=0
            ),
        )
        log.info(f"Job deleted for {job_name}")
    except client.exceptions.ApiException:
        log.info(f"Delete job {job_name} exception")
        if log.getEffectiveLevel() == logging.DEBUG:
            log.exception(f"Delete job {job_name} exception")
    except Exception:
        log.exception(f"Delete job {job_name} exception")


def create_cronjob(
    name: str,
    cronjob_name: str,
    job_name: str,
    namespace: str,
    workers: int,
    image: str,
    image_pull_secret: str,
    command: str,
    configmap: str,
    secret: str,
    mount_external_config: dict,
    mount_external_secret: dict,
    run_time: str,
    schedule: str,
):
    try:
        volumes, volume_mounts = get_volumes(
            mount_external_config, mount_external_secret
        )
        container = client.V1Container(
            name="locust",
            image=image,
            command=command,
            args=get_command_master(workers),
            ports=[
                client.V1ContainerPort(
                    host_port=5557, container_port=5557, name="master"
                ),
                client.V1ContainerPort(
                    host_port=8089, container_port=8089, name="metrics"
                ),
            ],
            env_from=get_env_from(secret, configmap),
            env=[client.V1EnvVar(name="LOCUST_RUN_TIME", value=run_time)],
            volume_mounts=volume_mounts,
        )
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(
                name=job_name, labels={"app": job_name, "locust": name}
            ),
            spec=client.V1PodSpec(
                restart_policy="Never",
                containers=[container],
                volumes=volumes,
                image_pull_secrets=get_image_pull_secret(image_pull_secret),
            ),
        )
        spec = client.V1JobSpec(
            template=template,
            backoff_limit=0,
            completions=1,
            parallelism=1,
            active_deadline_seconds=get_seconds(run_time),
        )
        spec_job_template = client.V1JobTemplateSpec(
            spec=spec,
            metadata=client.V1ObjectMeta(
                name=job_name, labels={"locust": name, "issued_by": "cronjob"}
            ),
        )
        spec_cronjob = client.V1CronJobSpec(
            concurrency_policy="Forbid",
            job_template=spec_job_template,
            schedule=schedule,
            suspend=False,
            failed_jobs_history_limit=1,
            successful_jobs_history_limit=1,
        )
        cronjob = client.V1CronJob(
            api_version="batch/v1",
            kind="CronJob",
            metadata=client.V1ObjectMeta(name=cronjob_name, labels={"locust": name}),
            spec=spec_cronjob,
        )
        api_instance = client.BatchV1Api()
        api_instance.create_namespaced_cron_job(body=cronjob, namespace=namespace)
        log.info(f"Cronjob created  for {cronjob_name}")
    except client.exceptions.ApiException:
        log.info(f"Create cronjob {cronjob_name} exception")
        if log.getEffectiveLevel() == logging.DEBUG:
            log.exception(f"Create cronjob {cronjob_name} exception")
    except Exception:
        log.exception(f"Create cronjob {cronjob_name} exception")


def update_cronjob(
    name: str,
    cronjob_name: str,
    job_name: str,
    namespace: str,
    workers: int,
    image: str,
    image_pull_secret: str,
    command: str,
    configmap: str,
    secret: str,
    mount_external_config: dict,
    mount_external_secret: dict,
    run_time: str,
    schedule: str,
):
    try:
        volumes, volume_mounts = get_volumes(
            mount_external_config, mount_external_secret
        )
        container = client.V1Container(
            name="locust",
            image=image,
            command=command,
            args=get_command_master(workers),
            ports=[
                client.V1ContainerPort(
                    host_port=5557, container_port=5557, name="master"
                ),
                client.V1ContainerPort(
                    host_port=8089, container_port=8089, name="metrics"
                ),
            ],
            env_from=get_env_from(secret, configmap),
            env=[client.V1EnvVar(name="LOCUST_RUN_TIME", value=run_time)],
            volume_mounts=volume_mounts,
        )
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(
                name=job_name, labels={"app": job_name, "locust": name}
            ),
            spec=client.V1PodSpec(
                restart_policy="Never",
                containers=[container],
                volumes=volumes,
                image_pull_secrets=get_image_pull_secret(image_pull_secret),
            ),
        )
        spec = client.V1JobSpec(
            template=template,
            backoff_limit=0,
            completions=1,
            parallelism=1,
            active_deadline_seconds=get_seconds(run_time),
        )
        spec_job_template = client.V1JobTemplateSpec(
            spec=spec,
            metadata=client.V1ObjectMeta(
                name=job_name, labels={"locust": name, "issued_by": "cronjob"}
            ),
        )
        spec_cronjob = client.V1CronJobSpec(
            concurrency_policy="Forbid",
            failed_jobs_history_limit=1,
            successful_jobs_history_limit=1,
            job_template=spec_job_template,
            schedule=schedule,
            suspend=False,
        )
        cronjob = client.V1CronJob(
            api_version="batch/v1",
            kind="CronJob",
            metadata=client.V1ObjectMeta(name=cronjob_name, labels={"locust": name}),
            spec=spec_cronjob,
        )
        api_instance = client.BatchV1Api()
        api_instance.replace_namespaced_cron_job(
            name=cronjob_name, body=cronjob, namespace=namespace
        )
        log.info(f"Cronjob updated for {cronjob_name}")
    except client.exceptions.ApiException:
        log.info(f"Update cronjob {cronjob_name} exception")
        if log.getEffectiveLevel() == logging.DEBUG:
            log.exception(f"Update cronjob {cronjob_name} exception")
    except Exception:
        log.exception(f"Update cronjob {cronjob_name} exception")


def delete_cronjob(cronjob_name: str, namespace: str):
    try:
        api_instance = client.BatchV1Api()
        api_instance.delete_namespaced_cron_job(
            name=cronjob_name,
            namespace=namespace,
            body=client.V1DeleteOptions(
                propagation_policy="Foreground", grace_period_seconds=0
            ),
        )
        log.info(f"Cronjob deleted for {cronjob_name}")
    except client.exceptions.ApiException:
        log.info(f"Delete cronjob {cronjob_name} exception")
        if log.getEffectiveLevel() == logging.DEBUG:
            log.exception(f"Delete cronjob {cronjob_name} exception")
    except Exception:
        log.exception(f"Delete cronjob {cronjob_name} exception")


def create_replica_set(
    name: str,
    replicaset_name: str,
    service_name: str,
    namespace: str,
    workers: int,
    image: str,
    image_pull_secret: str,
    command: str,
    configmap: str,
    secret: str,
    mount_external_config: dict,
    mount_external_secret: dict,
):
    try:
        volumes, volume_mounts = get_volumes(
            mount_external_config, mount_external_secret
        )
        container = client.V1Container(
            name="locust",
            image=image,
            command=command,
            args=get_command_worker(service_name),
            env_from=get_env_from(secret, configmap),
            volume_mounts=volume_mounts,
        )
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(name=replicaset_name, labels={"locust": name}),
            spec=client.V1PodSpec(
                containers=[container],
                volumes=volumes,
                image_pull_secrets=get_image_pull_secret(image_pull_secret),
            ),
        )
        spec = client.V1ReplicaSetSpec(
            selector=client.V1LabelSelector(match_labels={"locust": name}),
            replicas=workers,
            template=template,
        )
        replica_set = client.V1ReplicaSet(
            api_version="apps/v1",
            kind="ReplicaSet",
            metadata=client.V1ObjectMeta(name=replicaset_name, labels={"locust": name}),
            spec=spec,
        )
        api_instance = client.AppsV1Api()
        api_instance.create_namespaced_replica_set(
            body=replica_set, namespace=namespace
        )
        log.info(f"ReplicaSet created for {replicaset_name}")
    except client.exceptions.ApiException:
        log.info(f"Create replicaset {replicaset_name} exception")
        if log.getEffectiveLevel() == logging.DEBUG:
            log.exception(f"Create replicaset {replicaset_name} exception")
    except Exception:
        log.exception(f"Create replicaset {replicaset_name} exception")


def delete_replica_set(replicaset_name: str, namespace: str):
    try:
        api_instance = client.AppsV1Api()
        api_instance.delete_namespaced_replica_set(
            name=replicaset_name,
            namespace=namespace,
            body=client.V1DeleteOptions(
                propagation_policy="Foreground", grace_period_seconds=0
            ),
        )
        log.info(f"ReplicaSet deleted for {replicaset_name}")
    except client.exceptions.ApiException:
        log.info(f"Delete replicaset {replicaset_name} exception")
        if log.getEffectiveLevel() == logging.DEBUG:
            log.exception(f"Delete replicaset {replicaset_name} exception")
    except Exception:
        log.exception(f"Delete replicaset {replicaset_name} exception")


def delete_locust_object(
    group: str,
    version: str,
    namespace: str,
    plural: str,
    name: str,
):
    api_client = client.ApiClient()
    custom_api = client.CustomObjectsApi(api_client)
    try:
        custom_api.delete_namespaced_custom_object(
            group,
            version,
            namespace,
            plural,
            name,
        )
        log.info(f"Locust object {name} deleted.")
    except client.exceptions.ApiException:
        log.info(f"Delete Locust object {name} exception")
        if log.getEffectiveLevel() == logging.DEBUG:
            log.exception(f"Delete Locust object {name} exception")
    except Exception:
        log.exception(f"Delete Locust object {name} exception")


def get_locust_object(
    group: str,
    version: str,
    namespace: str,
    plural: str,
    name: str,
):
    api_client = client.ApiClient()
    custom_api = client.CustomObjectsApi(api_client)
    try:
        api_response = custom_api.get_namespaced_custom_object(
            group,
            version,
            namespace,
            plural,
            name,
        )
        log.info(f"Locust object {name} retrieved.")
        return api_response
    except client.exceptions.ApiException:
        log.info(f"Retrieve Locust object {name} exception")
        if log.getEffectiveLevel() == logging.DEBUG:
            log.exception(f"Retrieve Locust object {name} exception")
    except Exception:
        log.exception(f"Retrieve Locust object {name} exception")
