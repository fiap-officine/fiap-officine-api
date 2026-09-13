# ☸️ Kubernetes — PosFiap Setup Guide

This guide explains how to deploy the **PosFiap** application stack locally using Kubernetes.

---

## 📋 Prerequisites

Make sure you have the following installed and running:

| Tool | Purpose | Download |
|------|---------|----------|
| Docker Desktop | Container runtime | https://www.docker.com/products/docker-desktop |
| kubectl | Kubernetes CLI | https://kubernetes.io/docs/tasks/tools/ |
| Kubernetes (via Docker Desktop) | Local cluster | Enable in Docker Desktop → Settings → Kubernetes |

> **Verify your cluster is running before proceeding:**
> ```bash
> kubectl cluster-info
> ```
> You should see `Kubernetes control plane is running at https://kubernetes.docker.internal:6443`

---

## 🏗️ Architecture Overview

The stack runs inside a dedicated namespace `posfiap` with the following services:

```
┌─────────────────────────────────────────────────┐
│                  namespace: posfiap              │
│                                                  │
│   ┌──────────┐    ┌──────────┐   ┌──────────┐  │
│   │   API    │    │ Postgres │   │  Redis   │  │
│   │ :8000    │───▶│  :5432   │   │  :6379   │  │
│   │ (x2 pods)│    │ (x1 pod) │   │ (x1 pod) │  │
│   └──────────┘    └──────────┘   └──────────┘  │
│        │                │               │        │
│   ┌──────────┐          │               │        │
│   │  Worker  │──────────┘───────────────┘        │
│   │ (x1 pod) │                                   │
│   └──────────┘                                   │
└─────────────────────────────────────────────────┘
         │
         ▼
  NodePort :30800
  http://localhost:30800
```

| Component | Image | Replicas | Exposed Port |
|-----------|-------|----------|-------------|
| API | `gddarkness/fiap-oficina:latest` | 2 (auto-scales up to 10) | `localhost:30800` |
| Worker | `gddarkness/fiap-oficina:latest` | 1 | — (internal only) |
| PostgreSQL | `postgres` | 1 | — (internal only) |
| Redis | `redis` | 1 | — (internal only) |

---

## 🔐 Step 1 — Configure Secrets

The secrets file is **not committed to Git** for security reasons. You need to create it from the example:

```bash
cp secret.example.yaml secret.yaml
```

Then open `secret.yaml` and replace all placeholder values with real **Base64-encoded** values.

### How to encode a value to Base64

**Linux / macOS:**
```bash
echo -n "your_value_here" | base64
```

**Windows (PowerShell):**
```powershell
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your_value_here"))
```

### Secrets reference

| Key | Description | Example plain value |
|-----|-------------|---------------------|
| `DB_USER` | PostgreSQL username | `fiatech` |
| `DB_PASSWORD` | PostgreSQL password | `fiatech123` |
| `DB_NAME` | PostgreSQL database name | `oficina_db` |
| `POSTGRES_USER` | Same as `DB_USER` (used by the postgres container) | `fiatech` |
| `POSTGRES_PASSWORD` | Same as `DB_PASSWORD` | `fiatech123` |
| `POSTGRES_DB` | Same as `DB_NAME` | `oficina_db` |
| `JWT_SECRET_KEY` | Secret key for signing JWT tokens | `my-secret-key` |

> ⚠️ **Never commit `secret.yaml` to Git.** It is already listed in `.gitignore`.

---

## 🚀 Step 2 — Deploy to Kubernetes

Apply manifests **in this order** (dependencies first):

```bash
# 1. Create the namespace
kubectl apply -f namespace.yaml

# 2. Apply config and secrets
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml

# 3. Deploy the database and cache
kubectl apply -f postgres-deployment.yaml
kubectl apply -f postgres-svc.yaml
kubectl apply -f redis-deployment.yaml
kubectl apply -f redis-svc.yaml

# 4. Deploy the application
kubectl apply -f api-deployment.yaml
kubectl apply -f api-svc.yaml
kubectl apply -f api-hpa.yaml
kubectl apply -f worker-deployment.yaml
```

---

## ✅ Step 3 — Verify Everything is Running

```bash
kubectl get all -n posfiap
```

Expected output:

```
NAME                            READY   STATUS    RESTARTS   AGE
pod/api-xxxxx                   1/1     Running   0          1m
pod/api-yyyyy                   1/1     Running   0          1m
pod/postgres-xxxxx              1/1     Running   0          1m
pod/redis-xxxxx                 1/1     Running   0          1m
pod/worker-xxxxx                1/1     Running   0          1m

NAME               TYPE        CLUSTER-IP    PORT(S)          AGE
service/api        NodePort    10.x.x.x      8000:30800/TCP   1m
service/postgres   ClusterIP   10.x.x.x      5432/TCP         1m
service/redis      ClusterIP   10.x.x.x      6379/TCP         1m
```

All pods should show `Running` status. ✅

Once healthy, the API is available at:
```
http://localhost:30800
http://localhost:30800/docs   ← Swagger UI
```

---

## 🗂️ Files Reference

| File | Description |
|------|-------------|
| `namespace.yaml` | Creates the `posfiap` namespace |
| `configmap.yaml` | Non-sensitive environment variables (DB host, ports, JWT algorithm, etc.) |
| `secret.yaml` | Sensitive credentials in Base64 — **not committed to Git** |
| `secret.example.yaml` | Template for `secret.yaml` — safe to commit |
| `postgres-deployment.yaml` | PostgreSQL database deployment + PersistentVolumeClaim |
| `postgres-svc.yaml` | Internal ClusterIP service for PostgreSQL |
| `redis-deployment.yaml` | Redis cache deployment |
| `redis-svc.yaml` | Internal ClusterIP service for Redis |
| `api-deployment.yaml` | FastAPI application deployment (2 replicas, runs Alembic migrations on init) |
| `api-svc.yaml` | NodePort service exposing the API on port `30800` |
| `api-hpa.yaml` | HorizontalPodAutoscaler — scales API from 2 to 10 pods based on CPU/memory |
| `worker-deployment.yaml` | Background task worker deployment |

---

## 🛠️ Useful Commands

```bash
# Watch pod status in real time
kubectl get pods -n posfiap -w

# Check logs for a specific pod
kubectl logs <pod-name> -n posfiap

# Follow logs (stream)
kubectl logs -f <pod-name> -n posfiap

# Describe a pod (useful for debugging crashes)
kubectl describe pod <pod-name> -n posfiap

# Check secrets (values are hidden, only sizes shown)
kubectl describe secret posfiap-secrets -n posfiap

# Check HPA (autoscaler) status
kubectl get hpa -n posfiap
```

---

## 🔄 Updating / Redeploying

After changing any manifest file:

```bash
kubectl apply -f <changed-file>.yaml
```

After updating the Docker image (new release):

```bash
# Force pods to pull the latest image
kubectl rollout restart deployment/api -n posfiap
kubectl rollout restart deployment/worker -n posfiap

# Watch the rollout
kubectl rollout status deployment/api -n posfiap
```

---

## 🧹 Teardown

To remove everything:

```bash
# Delete all resources in the namespace
kubectl delete namespace posfiap
```

> This will delete all pods, services, deployments, secrets, configmaps, and PersistentVolumeClaims inside `posfiap`.

---

## ❓ Troubleshooting

### Pod is in `CrashLoopBackOff`
```bash
kubectl logs <pod-name> -n posfiap
kubectl describe pod <pod-name> -n posfiap
```
Check the logs for errors. Common causes:
- Missing or incorrect secret values in `secret.yaml`
- Database not ready yet (the API has an init container that runs Alembic migrations — wait for it)
- Application error on startup

### `ImagePullBackOff`
The Docker image can't be pulled. Make sure Docker is running and you have access to the image registry.

### `Pending` pods
```bash
kubectl describe pod <pod-name> -n posfiap
```
Usually caused by insufficient resources. Check the `Events` section at the bottom of the describe output.
