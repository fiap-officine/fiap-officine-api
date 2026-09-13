# ─────────────────────────────────────────────────────────────────────────────
# Cluster Configuration
# ─────────────────────────────────────────────────────────────────────────────

variable "kubeconfig_path" {
  description = "Path to the kubeconfig file"
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "Kubernetes context to use (e.g. docker-desktop, minikube)"
  type        = string
  default     = "docker-desktop"
}

variable "namespace" {
  description = "Kubernetes namespace for all resources"
  type        = string
  default     = "posfiap"
}

# ─────────────────────────────────────────────────────────────────────────────
# Database Secrets
# ─────────────────────────────────────────────────────────────────────────────

variable "db_user" {
  description = "PostgreSQL database username"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "PostgreSQL database password"
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  sensitive   = true
}

# ─────────────────────────────────────────────────────────────────────────────
# Application Secrets
# ─────────────────────────────────────────────────────────────────────────────

variable "jwt_secret_key" {
  description = "Secret key used to sign JWT tokens"
  type        = string
  sensitive   = true
}

variable "webhook_shared_secret" {
  description = "Shared secret required in the x-webhook-token header for webhook endpoints"
  type        = string
  sensitive   = true
}

# ─────────────────────────────────────────────────────────────────────────────
# Application Config
# ─────────────────────────────────────────────────────────────────────────────

variable "app_env" {
  description = "Application environment (production, staging, development)"
  type        = string
  default     = "production"
}

variable "app_debug" {
  description = "Enable application debug mode"
  type        = string
  default     = "false"
}

variable "jwt_algorithm" {
  description = "JWT signing algorithm"
  type        = string
  default     = "HS256"
}

variable "jwt_expire_minutes" {
  description = "JWT access token expiration in minutes"
  type        = string
  default     = "60"
}

# ─────────────────────────────────────────────────────────────────────────────
# API Scaling
# ─────────────────────────────────────────────────────────────────────────────

variable "api_min_replicas" {
  description = "Minimum number of API replicas"
  type        = number
  default     = 2
}

variable "api_max_replicas" {
  description = "Maximum number of API replicas (HPA)"
  type        = number
  default     = 10
}

variable "api_node_port" {
  description = "NodePort to expose the API externally"
  type        = number
  default     = 30800
}

# ─────────────────────────────────────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────────────────────────────────────

variable "postgres_storage_size" {
  description = "PersistentVolumeClaim size for PostgreSQL data"
  type        = string
  default     = "5Gi"
}
