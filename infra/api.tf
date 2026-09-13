
locals {
  api_image = "gddarkness/fiap-oficina:latest"

  secret_env = [
    { name = "DB_USER", key = "DB_USER" },
    { name = "DB_PASSWORD", key = "DB_PASSWORD" },
    { name = "DB_NAME", key = "DB_NAME" },
    { name = "JWT_SECRET_KEY", key = "JWT_SECRET_KEY" },
    { name = "WEBHOOK_SHARED_SECRET", key = "WEBHOOK_SHARED_SECRET" },
  ]
}

resource "kubernetes_deployment" "api" {
  metadata {
    name      = "api"
    namespace = kubernetes_namespace.posfiap.metadata[0].name

    labels = {
      "app.kubernetes.io/name"      = var.namespace
      "app.kubernetes.io/component" = "api"
    }
  }

  spec {
    replicas = var.api_min_replicas

    selector {
      match_labels = {
        app = "api"
      }
    }

    template {
      metadata {
        labels = {
          app                           = "api"
          "app.kubernetes.io/component" = "api"
        }
      }

      spec {
        # ── Init container: run Alembic DB migrations before starting the API ──
        init_container {
          name    = "alembic-migrate"
          image   = local.api_image
          command = ["uv", "run", "alembic", "upgrade", "head"]

          env_from {
            config_map_ref {
              name = kubernetes_config_map.posfiap_config.metadata[0].name
            }
          }

          dynamic "env" {
            for_each = local.secret_env
            content {
              name = env.value.name
              value_from {
                secret_key_ref {
                  name = kubernetes_secret.posfiap_secrets.metadata[0].name
                  key  = env.value.key
                }
              }
            }
          }
        }

        container {
          name    = "api"
          image   = local.api_image
          command = ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

          port {
            name           = "http"
            container_port = 8000
            protocol       = "TCP"
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map.posfiap_config.metadata[0].name
            }
          }

          dynamic "env" {
            for_each = local.secret_env
            content {
              name = env.value.name
              value_from {
                secret_key_ref {
                  name = kubernetes_secret.posfiap_secrets.metadata[0].name
                  key  = env.value.key
                }
              }
            }
          }

          liveness_probe {
            http_get {
              path = "/docs"
              port = 8000
            }
            initial_delay_seconds = 30
            period_seconds        = 15
            timeout_seconds       = 5
            failure_threshold     = 3
          }

          readiness_probe {
            http_get {
              path = "/docs"
              port = 8000
            }
            initial_delay_seconds = 10
            period_seconds        = 10
            timeout_seconds       = 3
            failure_threshold     = 3
          }

          resources {
            requests = {
              cpu    = "250m"
              memory = "256Mi"
            }
            limits = {
              cpu    = "500m"
              memory = "512Mi"
            }
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [spec[0].replicas]
  }
}


resource "kubernetes_service" "api" {
  metadata {
    name      = "api"
    namespace = kubernetes_namespace.posfiap.metadata[0].name

    labels = {
      "app.kubernetes.io/name"      = var.namespace
      "app.kubernetes.io/component" = "api"
    }
  }

  spec {
    type = "NodePort"

    selector = {
      app = "api"
    }

    port {
      name        = "http"
      protocol    = "TCP"
      port        = 8000
      target_port = 8000
      node_port   = var.api_node_port
    }
  }
}


resource "kubernetes_horizontal_pod_autoscaler_v2" "api_hpa" {
  metadata {
    name      = "api-hpa"
    namespace = kubernetes_namespace.posfiap.metadata[0].name

    labels = {
      "app.kubernetes.io/name"      = var.namespace
      "app.kubernetes.io/component" = "api"
    }
  }

  spec {
    min_replicas = var.api_min_replicas
    max_replicas = var.api_max_replicas

    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = kubernetes_deployment.api.metadata[0].name
    }

    metric {
      type = "Resource"
      resource {
        name = "cpu"
        target {
          type                = "Utilization"
          average_utilization = 70
        }
      }
    }

    metric {
      type = "Resource"
      resource {
        name = "memory"
        target {
          type                = "Utilization"
          average_utilization = 80
        }
      }
    }

    behavior {
      scale_up {
        stabilization_window_seconds = 30
        select_policy                = "Max"
        policy {
          type           = "Pods"
          value          = 4
          period_seconds = 60
        }
      }

      scale_down {
        stabilization_window_seconds = 120
        select_policy                = "Min"
        policy {
          type           = "Pods"
          value          = 1
          period_seconds = 120
        }
      }
    }
  }
}
