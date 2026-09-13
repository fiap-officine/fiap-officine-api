
resource "kubernetes_config_map" "posfiap_config" {
  metadata {
    name      = "posfiap-config"
    namespace = kubernetes_namespace.posfiap.metadata[0].name

    labels = {
      "app.kubernetes.io/name"      = var.namespace
      "app.kubernetes.io/component" = "config"
    }
  }

  data = {
    DB_HOST                          = "postgres"
    DB_PORT                          = "5432"
    REDIS_HOST                       = "redis"
    REDIS_PORT                       = "6379"
    REDIS_DB                         = "0"
    JWT_ALGORITHM                    = var.jwt_algorithm
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES  = var.jwt_expire_minutes
    APP_ENV                          = var.app_env
    APP_DEBUG                        = var.app_debug
  }
}
