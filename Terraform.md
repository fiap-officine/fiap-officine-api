# 🏗️ Terraform — PosFiap On-Premise Setup

This directory contains Terraform scripts to deploy the **PosFiap** application stack on a local Kubernetes cluster (Docker Desktop, Minikube, etc.) using the [Terraform Kubernetes Provider](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs).

---

## 📋 Prerequisites

| Tool | Min Version | Install |
|------|-------------|---------|
| Terraform | >= 1.6.0 | https://developer.hashicorp.com/terraform/downloads |
| kubectl | any | https://kubernetes.io/docs/tasks/tools/ |
| Docker Desktop + Kubernetes | any | Enable in Docker Desktop → Settings → Kubernetes |

Verify your cluster is running:
```bash
kubectl cluster-info
```

---

## 📁 File Structure

```
infra/
├── providers.tf              # Kubernetes provider config
├── variables.tf              # All input variable definitions
├── terraform.tfvars.example  # Template — copy to terraform.tfvars
├── terraform.tfvars          # Your real values (NOT committed to Git)
├── namespace.tf              # posfiap namespace
├── configmap.tf              # Non-sensitive environment config
├── secret.tf                 # Sensitive credentials
├── postgres.tf               # PostgreSQL PVC + Deployment + Service
├── redis.tf                  # Redis Deployment + Service
├── api.tf                    # API Deployment + NodePort Service + HPA
├── worker.tf                 # Background Worker Deployment
├── outputs.tf                # Useful URLs and service names after apply
└── README.md                 # This file
```

---

## 🔐 Step 1 — Configure Secrets

```bash
cp terraform.tfvars.example terraform.tfvars
```

Open `terraform.tfvars` and fill in your values:

```hcl
db_user        = "fiatech"
db_password    = "your_secure_password"
db_name        = "oficina_db"
jwt_secret_key = "your-super-secret-jwt-key"
```

> ⚠️ `terraform.tfvars` is in `.gitignore` — never commit it.

> 💡 Unlike the raw Kubernetes approach, Terraform handles Base64 encoding automatically. Just provide plain text values.

---

## 🚀 Step 2 — Deploy

```bash
# Initialize Terraform (downloads the Kubernetes provider)
terraform init

# Preview what will be created
terraform plan

# Apply — creates all resources in the cluster
terraform apply
```

Type `yes` when prompted.

---

## ✅ Step 3 — Verify

After a successful apply, Terraform prints the outputs:

```
Outputs:

api_docs_url    = "http://localhost:30800/docs"
api_node_port   = 30800
api_url         = "http://localhost:30800"
namespace       = "posfiap"
postgres_service = "postgres.posfiap.svc.cluster.local:5432"
redis_service    = "redis.posfiap.svc.cluster.local:6379"
```

Check that all pods are running:
```bash
kubectl get all -n posfiap
```

---

## ⚙️ Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `kubeconfig_path` | `~/.kube/config` | Path to kubeconfig file |
| `kube_context` | `docker-desktop` | Kubernetes context to use |
| `namespace` | `posfiap` | Namespace for all resources |
| `db_user` | _(required)_ | PostgreSQL username |
| `db_password` | _(required)_ | PostgreSQL password |
| `db_name` | _(required)_ | PostgreSQL database name |
| `jwt_secret_key` | _(required)_ | JWT signing secret |
| `app_env` | `production` | App environment |
| `app_debug` | `false` | Enable debug mode |
| `api_min_replicas` | `2` | Minimum API pods |
| `api_max_replicas` | `10` | Maximum API pods (HPA limit) |
| `api_node_port` | `30800` | External port for the API |
| `postgres_storage_size` | `5Gi` | PostgreSQL PVC size |

---

## 🔄 Updating Resources

After changing any `.tf` file:

```bash
terraform plan   # preview changes
terraform apply  # apply changes
```

To force a new pod rollout (e.g., after a new image is pushed):
```bash
kubectl rollout restart deployment/api -n posfiap
kubectl rollout restart deployment/worker -n posfiap
```

---

## 🧹 Teardown

To destroy all Kubernetes resources created by Terraform:

```bash
terraform destroy
```

> ⚠️ This will delete all resources including the PostgreSQL PersistentVolumeClaim and its data.

---

## ❓ Troubleshooting

### HPA shows `<unknown>` for CPU/Memory targets
The Metrics Server is not installed. Install it:
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### `Error: context not found`
Your `kube_context` in `terraform.tfvars` doesn't match any context in your kubeconfig. List available contexts:
```bash
kubectl config get-contexts
```

### API pods in `CrashLoopBackOff`
Check logs:
```bash
kubectl logs -l app=api -n posfiap --tail=50
```
