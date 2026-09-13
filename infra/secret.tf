# ─────────────────────────────────────────────────────────────────────────────
# Secret — Sensitive credentials
# Values are passed via terraform.tfvars (never committed to Git).
# Terraform automatically Base64-encodes values in the `data` block.
# ─────────────────────────────────────────────────────────────────────────────

resource "kubernetes_secret" "posfiap_secrets" {
  metadata {
    name      = "posfiap-secrets"
    namespace = kubernetes_namespace.posfiap.metadata[0].name

    labels = {
      "app.kubernetes.io/name"      = var.namespace
      "app.kubernetes.io/component" = "secrets"
    }
  }

  type = "Opaque"

  data = {
    DB_USER           = var.db_user
    DB_PASSWORD       = var.db_password
    DB_NAME           = var.db_name
    POSTGRES_USER     = var.db_user
    POSTGRES_PASSWORD = var.db_password
    POSTGRES_DB       = var.db_name
    JWT_SECRET_KEY    = var.jwt_secret_key
    WEBHOOK_SHARED_SECRET = var.webhook_shared_secret
  }
}
