# Deploy locust example

Example for run a benchmark test:

    helm upgrade --create-namespace --namespace locust --debug --install --wait locust-run examples/chart-minimal/

Example for run a scheduled benchmark test:

    helm upgrade --create-namespace --namespace locust --set schedule="*/5 * * * *" --debug --install --wait locust-run examples/chart-minimal/
