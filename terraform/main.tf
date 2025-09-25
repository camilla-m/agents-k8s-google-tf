# Google ADK Travel System - Terraform Infrastructure
# Creates GKE cluster and supporting infrastructure for ADK deployment

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Data sources
data "google_client_config" "default" {}

# VPC Network for the cluster
resource "google_compute_network" "adk_vpc" {
  name                    = "${var.cluster_name}-vpc"
  auto_create_subnetworks = false
  description             = "VPC network for Google ADK Travel System"
  
  timeouts {
    create = "5m"
    delete = "5m"
  }
}

# Subnet for the GKE cluster
resource "google_compute_subnetwork" "adk_subnet" {
  name          = "${var.cluster_name}-subnet"
  ip_cidr_range = var.vpc_cidr_range
  region        = var.region
  network       = google_compute_network.adk_vpc.id
  description   = "Subnet for Google ADK Travel System GKE cluster"

  # Secondary ranges for pods and services
  secondary_ip_range {
    range_name    = "pod-ranges"
    ip_cidr_range = var.pod_cidr_range
  }

  secondary_ip_range {
    range_name    = "services-range"
    ip_cidr_range = var.services_cidr_range
  }

  # Enable private Google access for nodes to reach Google APIs
  private_ip_google_access = true
}

# Firewall rules
resource "google_compute_firewall" "adk_allow_internal" {
  name    = "${var.cluster_name}-allow-internal"
  network = google_compute_network.adk_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [var.vpc_cidr_range, var.pod_cidr_range, var.services_cidr_range]
  description   = "Allow internal communication within the ADK cluster"

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_firewall" "adk_allow_ssh" {
  name    = "${var.cluster_name}-allow-ssh"
  network = google_compute_network.adk_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"] # Google Cloud Shell and IAP ranges
  target_tags   = ["ssh-allowed"]
  description   = "Allow SSH access from Cloud Shell and IAP"
}

# GKE Cluster
resource "google_container_cluster" "adk_cluster" {
  name     = var.cluster_name
  location = var.region
  
  initial_node_count       = 1
  
  # Enable Autopilot for simplified management and better resource efficiency
  enable_autopilot = var.enable_autopilot
  
  # Network configuration
  network    = google_compute_network.adk_vpc.name
  subnetwork = google_compute_subnetwork.adk_subnet.name

  # IP allocation policy for pods and services
  ip_allocation_policy {
    cluster_secondary_range_name  = "pod-ranges"
    services_secondary_range_name = "services-range"
  }

  # Master authorized networks
  dynamic "master_authorized_networks_config" {
    for_each = var.master_authorized_networks
    content {
      dynamic "cidr_blocks" {
        for_each = var.master_authorized_networks
        content {
          cidr_block   = cidr_blocks.value.cidr_block
          display_name = cidr_blocks.value.display_name
        }
      }
    }
  }

  # Enable workload identity for secure pod-to-GCP communication
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Logging and monitoring configuration
  logging_service    = "logging.googleapis.com/kubernetes"
  monitoring_service = "monitoring.googleapis.com/kubernetes"

  # Enable additional features
  addons_config {
    http_load_balancing {
      disabled = false
    }
    horizontal_pod_autoscaling {
      disabled = false
    }
    gcs_fuse_csi_driver_config {
      enabled = false # Not needed for ADK workloads
    }
  }

  # Maintenance policy
  maintenance_policy {
    daily_maintenance_window {
      start_time = var.maintenance_start_time
    }
  }

  # Resource labels
  resource_labels = merge(var.resource_labels, {
    environment = var.environment
    component   = "gke-cluster"
    workload    = "adk-travel-system"
  })
  
  # Binary authorization (disabled for development, enable in production)
  binary_authorization {
    evaluation_mode = "DISABLED"
  }

  # Private cluster configuration (optional - uncomment for private cluster)
  # private_cluster_config {
  #   enable_private_nodes    = true
  #   enable_private_endpoint = false
  #   master_ipv4_cidr_block  = "172.16.0.0/28"
  # }

  timeouts {
    create = "30m"
    update = "20m"
    delete = "20m"
  }

  # Ignore changes to node_config since we're using Autopilot
  lifecycle {
    ignore_changes = [
      node_config,
      initial_node_count,
    ]
  }
}

# Service account for ADK workloads (if not using Autopilot default)
resource "google_service_account" "adk_workload_identity" {
  count        = var.enable_autopilot ? 0 : 1
  account_id   = "${var.cluster_name}-wi-sa"
  display_name = "Workload Identity Service Account for ${var.cluster_name}"
  description  = "Service account for ADK workloads with Workload Identity"
}

# IAM bindings for the workload identity service account
resource "google_project_iam_member" "adk_workload_identity_roles" {
  count   = var.enable_autopilot ? 0 : length(local.workload_identity_roles)
  project = var.project_id
  role    = local.workload_identity_roles[count.index]
  member  = "serviceAccount:${google_service_account.adk_workload_identity[0].email}"
}

locals {
  workload_identity_roles = [
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/aiplatform.user",
  ]
}

# Enable Workload Identity binding (if not using Autopilot)
resource "google_service_account_iam_member" "adk_workload_identity_binding" {
  count              = var.enable_autopilot ? 0 : 1
  service_account_id = google_service_account.adk_workload_identity[0].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[adk-travel/adk-agents]"
}

# Cloud SQL instance (optional - for conversation persistence)
resource "google_sql_database_instance" "adk_postgres" {
  count            = var.enable_cloud_sql ? 1 : 0
  name             = "${var.cluster_name}-postgres"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-f1-micro"
    
    backup_configuration {
      enabled    = true
      start_time = "03:00"
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.adk_vpc.id
      require_ssl     = true
    }

    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }

    database_flags {
      name  = "log_connections"
      value = "on"
    }

    database_flags {
      name  = "log_disconnections"
      value = "on"
    }
  }

  deletion_protection = false # Set to true in production
}

resource "google_sql_database" "adk_database" {
  count    = var.enable_cloud_sql ? 1 : 0
  name     = "adk_conversations"
  instance = google_sql_database_instance.adk_postgres[0].name
}

resource "google_sql_user" "adk_user" {
  count    = var.enable_cloud_sql ? 1 : 0
  name     = "adk_app"
  instance = google_sql_database_instance.adk_postgres[0].name
  password = var.db_password
}

# Private Service Connection for Cloud SQL (if enabled)
resource "google_compute_global_address" "private_ip_address" {
  count         = var.enable_cloud_sql ? 1 : 0
  name          = "${var.cluster_name}-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.adk_vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  count                   = var.enable_cloud_sql ? 1 : 0
  network                 = google_compute_network.adk_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address[0].name]
}