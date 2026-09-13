terraform {
  required_version = ">= 1.6.0"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Kubernetes Provider — On-Premise / Local Cluster
# Reads credentials from your local kubeconfig file.
# Defaults to the current context (e.g., docker-desktop).
# ─────────────────────────────────────────────────────────────────────────────
provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kube_context
}
