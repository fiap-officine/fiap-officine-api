
resource "kubernetes_deployment" "worker" {
  metadata {
    name      = "worker"
    namespace = kubernetes_namespace.posfiap.metadata[0].name

    labels = {
      "app.kubernetes.io/name"      = var.namespace
      "app.kubernetes.io/component" = "worker"
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "worker"
      }
    }

    template {
      metadata {
        labels = {
          app                           = "worker"
          "app.kubernetes.io/component" = "worker"
        }
      }

      spec {
        container {
          name    = "worker"
          image   = local.api_image
          command = ["uv", "run", "python", "-m", "app.worker"]

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

          resources {
            requests = {
              cpu    = "100m"
              memory = "128Mi"
            }
            limits = {
              cpu    = "300m"
              memory = "256Mi"
            }
          }
        }
      }
    }
  }
}
