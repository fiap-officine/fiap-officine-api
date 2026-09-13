
resource "kubernetes_namespace" "posfiap" {
  metadata {
    name = var.namespace

    labels = {
      "app.kubernetes.io/name"       = var.namespace
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}
