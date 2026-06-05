output "cluster_endpoint" {
  description = "The IP address of the GKE cluster master"
  value       = google_container_cluster.adk_cluster.endpoint
}

output "artifact_registry_url" {
  description = "The URL of the Artifact Registry repository"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/adk-travel"
}
