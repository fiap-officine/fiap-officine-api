output "namespace" {
  description = "Kubernetes namespace where all resources are deployed"
  value       = kubernetes_namespace.posfiap.metadata[0].name
}

output "api_url" {
  description = "URL to access the API locally"
  value       = "http://localhost:${var.api_node_port}"
}

output "api_docs_url" {
  description = "URL to access the Swagger UI"
  value       = "http://localhost:${var.api_node_port}/docs"
}

output "api_node_port" {
  description = "NodePort assigned to the API service"
  value       = var.api_node_port
}

output "postgres_service" {
  description = "Internal DNS name for PostgreSQL (accessible inside the cluster)"
  value       = "postgres.${kubernetes_namespace.posfiap.metadata[0].name}.svc.cluster.local:5432"
}

output "redis_service" {
  description = "Internal DNS name for Redis (accessible inside the cluster)"
  value       = "redis.${kubernetes_namespace.posfiap.metadata[0].name}.svc.cluster.local:6379"
}
