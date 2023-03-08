# Deploy operator

The chart will setup everything required to run the operator.

## Via Helm

### Use Git repo

    git clone git@github.com:treussart/locust-operator.git
    helm upgrade --create-namespace --namespace locust --debug --install --wait locust-operator chart/

## Values

| Key                       | Type   | Default | Description |
|---------------------------|--------|---------|-------------|
| metrics.enabled           | bool   | `false` |  |
| resources.requests.cpu    | string | `100m`  |  |
| resources.requests.memory | string | `100Mi` |  |
| resources.limits.cpu      | string | `100m`  |  |
| resources.limits.memory   | string | `100Mi` |  |
