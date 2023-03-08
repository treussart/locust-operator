import logging
import os

from kubernetes import config
from prometheus_client import start_http_server

from src.args import get_args
from src.constants import (
    CRD_GROUP,
    CRD_VERSION,
    NAMESPACE,
    CRD_PLURAL,
    GAUGE_LOCUST_OBJECT,
    ENUM_LOCUST_OBJECT_STATE,
    GAUGE_JOB_OBJECT,
    ENUM_JOB_OBJECT_STATE,
)
from src.controller import check_crd
from src.listeners import watch_locust_events, watch_job_via_thread, watch_job_events

logging.basicConfig(
    format="%(levelname)s: %(message)s", level=os.getenv("LOG_LEVEL", logging.INFO)
)


def main():
    args = get_args()
    # Check if run in k8s cluster and load the kubeconfig
    if "KUBERNETES_PORT" in os.environ:
        config.load_incluster_config()
    else:
        config.load_kube_config()
    # Run the controller
    check_crd(CRD_GROUP, CRD_VERSION, NAMESPACE, CRD_PLURAL)
    if args.jobs:
        # Start up the server to expose the metrics.
        start_http_server(8000)
        watch_job_events(
            CRD_GROUP,
            CRD_VERSION,
            NAMESPACE,
            CRD_PLURAL,
            GAUGE_JOB_OBJECT,
            ENUM_JOB_OBJECT_STATE,
        )
    elif args.locusts:
        # Start up the server to expose the metrics.
        start_http_server(8001)
        watch_locust_events(
            CRD_GROUP,
            CRD_VERSION,
            NAMESPACE,
            CRD_PLURAL,
            GAUGE_LOCUST_OBJECT,
            ENUM_LOCUST_OBJECT_STATE,
        )
    else:
        # Start up the server to expose the metrics.
        start_http_server(8000)
        watch_job_via_thread(
            CRD_GROUP,
            CRD_VERSION,
            NAMESPACE,
            CRD_PLURAL,
            GAUGE_JOB_OBJECT,
            ENUM_JOB_OBJECT_STATE,
        )
        watch_locust_events(
            CRD_GROUP,
            CRD_VERSION,
            NAMESPACE,
            CRD_PLURAL,
            GAUGE_LOCUST_OBJECT,
            ENUM_LOCUST_OBJECT_STATE,
        )


if __name__ == "__main__":
    main()
