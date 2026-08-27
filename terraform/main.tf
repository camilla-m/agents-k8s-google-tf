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
  deletion_protection      = false
  
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
  # google_container_cluster only accepts a single master_authorized_networks_config
  # block; the list of allowed CIDRs goes in its repeatable nested cidr_blocks. The
  # previous version put the dynamic on the outer block too, which both produced one
  # (duplicated) outer block per entry instead of one, and would error outright as
  # soon as master_authorized_networks had more than one entry.
  dynamic "master_authorized_networks_config" {
    for_each = length(var.master_authorized_networks) > 0 ? [var.master_authorized_networks] : []
    content {
      dynamic "cidr_blocks" {
        for_each = master_authorized_networks_config.value
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

  # Node configuration for standard cluster (ignored if Autopilot is enabled)
  dynamic "node_config" {
    for_each = var.enable_autopilot ? [] : [1]
    content {
      machine_type = var.machine_type
      disk_size_gb = var.disk_size_gb
      disk_type    = var.disk_type
      oauth_scopes = var.oauth_scopes
      
      metadata = {
        disable-legacy-endpoints = "true"
      }
      
      workload_metadata_config {
        mode = "GKE_METADATA"
      }
      
      shielded_instance_config {
        enable_secure_boot          = var.enable_shielded_nodes
        enable_integrity_monitoring = var.enable_shielded_nodes
      }
      
      preemptible = var.preemptible
      labels      = var.resource_labels
    }
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

# NOTE: this used to also create a second service account ("<cluster>-wi-sa") with its
# own IAM roles and a Workload Identity binding to the same adk-travel/adk-agents KSA
# that scripts/setup.sh already binds to $service_account_name (adk-travel-sa, the GSA
# that k8s/sa.yaml's iam.gke.io/gcp-service-account annotation actually points at).
# That second GSA was never referenced anywhere - pure dead weight - and its binding
# resource had no depends_on the cluster, so Terraform tried to create it in parallel
# with google_container_cluster.adk_cluster and failed outright ("Identity Pool does
# not exist") because the $project_id.svc.id.goog pool isn't provisioned until the
# cluster (with workload_identity_config) actually exists. Removed rather than patched
# with depends_on, since nothing used it. The real GSA/KSA binding for the pods is done
# by scripts/setup.sh (gcloud iam service-accounts add-iam-policy-binding), run after
# this Terraform apply so the cluster - and its Workload Identity pool - already exist.