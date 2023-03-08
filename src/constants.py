import os

from prometheus_client import Gauge, Enum

CRD_GROUP = "locust-qa.xyz"
CRD_VERSION = "v1"
CRD_PLURAL = "locusts"
CRD_NAME = "Locust"
NAMESPACE = os.getenv("NAMESPACE", "locust")
PREFIX_STATS = "locust_operator"
GAUGE_LOCUST_OBJECT = Gauge(
    f"{PREFIX_STATS}_locust_object_gauge",
    "Gauge Locust object",
    labelnames=["operation", "name"],
)
ENUM_LOCUST_OBJECT_STATE = Enum(
    f"{PREFIX_STATS}_locust_object_state",
    "State of Locust object",
    states=["starting", "running", "stopped"],
    labelnames=["name"],
)
GAUGE_JOB_OBJECT = Gauge(
    f"{PREFIX_STATS}_job_object_gauge",
    "Gauge Job object",
    labelnames=["operation", "name", "job_name"],
)
ENUM_JOB_OBJECT_STATE = Enum(
    f"{PREFIX_STATS}_job_object_state",
    "State of Job object",
    states=["starting", "running", "stopped"],
    labelnames=["name", "job_name", "status"],
)
ADDITIONAL_ACTIVE_DEADLINE_MINUTES = 5
