# Development

## Run locally

    echo 'NAMESPACE="locust"' >.env

    kubectl apply -f chart/crds/locust.yaml

    PYTHONPATH=$PYTHONPATH:$(pwd)/src pipenv run operator

    helm upgrade --create-namespace --namespace locust --debug --install --wait locust-run examples/chart-minimal/
    or
    helm upgrade --set schedule="*/2 * * * *" --create-namespace --namespace locust --debug --install --wait locust-run examples/chart-minimal/

    helm uninstall -n locust locust-run

if operator failed:

    kubectl delete -n locust service/service-locust-run
    kubectl delete -n locust job/job-locust-run
    kubectl delete -n locust cronjob/cronjob-locust-run
    kubectl delete -n locust replicaset/replicaset-locust-run
