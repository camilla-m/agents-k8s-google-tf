

variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
  validation {
    condition     = length(var.project_id) > 0
    error_message = "Project ID cannot be empty."
  }
}

variable "region" {
  description = "The Google Cloud region for resources"
  type        = string
  default     = "us-central1"
}

variable "cluster_name" {
  description = "Name of the GKE cluster"
  type        = string
  default     = "adk-travel-cluster"
}

variable "namespace" {
  description = "Kubernetes namespace for the application"
  type        = string
  default     = "adk-travel"
}

# Network CIDR ranges
variable "vpc_cidr_range" {
  description = "CIDR block for the VPC subnet"
  type        = string
  default     = "10.0.0.0/16"
}

variable "pod_cidr_range" {
  description = "CIDR block for pods"
  type        = string
  default     = "10.1.0.0/16"
}

variable "services_cidr_range" {
  description = "CIDR block for services"
  type        = string
  default     = "10.2.0.0/16"
}

# Master authorized networks
variable "master_authorized_networks" {
  description = "List of master authorized networks"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = [
    {
      cidr_block   = "0.0.0.0/0"
      display_name = "All"
    }
  ]
}

# Resource labels
variable "resource_labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default = {
    project     = "adk-travel"
    environment = "development"
    managed-by  = "terraform"
  }
}

# Node configuration
variable "node_count" {
  description = "Number of nodes in the default node pool"
  type        = number
  default     = 3
}

variable "machine_type" {
  description = "Machine type for GKE nodes"
  type        = string
  default     = "e2-standard-4"
}

variable "disk_size_gb" {
  description = "Disk size in GB for each node"
  type        = number
  default     = 100
}

variable "min_node_count" {
  description = "Minimum number of nodes in the node pool"
  type        = number
  default     = 1
}

variable "max_node_count" {
  description = "Maximum number of nodes in the node pool"
  type        = number
  default     = 5
}

variable "enable_autoscaling" {
  description = "Enable cluster autoscaling"
  type        = bool
  default     = true
}

variable "enable_autopilot" {
  description = "Enable GKE Autopilot mode"
  type        = bool
  default     = false
}

variable "kubernetes_version" {
  description = "Kubernetes version for the cluster"
  type        = string
  default     = "latest"
}

# Network configuration
variable "network_name" {
  description = "Name of the VPC network"
  type        = string
  default     = "adk-travel-vpc"
}

variable "subnet_name" {
  description = "Name of the subnet"
  type        = string
  default     = "adk-travel-subnet"
}

variable "enable_ip_alias" {
  description = "Enable IP alias for the cluster"
  type        = bool
  default     = true
}

variable "enable_private_nodes" {
  description = "Enable private nodes"
  type        = bool
  default     = true
}

variable "master_ipv4_cidr_block" {
  description = "CIDR block for the master network"
  type        = string
  default     = "172.16.0.0/28"
}

variable "enable_network_policy" {
  description = "Enable network policy"
  type        = bool
  default     = true
}

variable "enable_workload_identity" {
  description = "Enable Workload Identity"
  type        = bool
  default     = true
}

variable "maintenance_start_time" {
  description = "Start time for maintenance window (HH:MM in UTC)"
  type        = string
  default     = "02:00"
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default = {
    project     = "adk-travel"
    environment = "development"
    managed-by  = "terraform"
  }
}

variable "enable_monitoring" {
  description = "Enable Google Cloud Monitoring"
  type        = bool
  default     = true
}

variable "enable_logging" {
  description = "Enable Google Cloud Logging"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Log retention period in days"
  type        = number
  default     = 30
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "development"
}

# Additional variables that might be referenced
variable "zone" {
  description = "The zone for single-zone resources"
  type        = string
  default     = ""
}

variable "enable_binary_authorization" {
  description = "Enable binary authorization"
  type        = bool
  default     = false
}

variable "enable_shielded_nodes" {
  description = "Enable shielded nodes"
  type        = bool
  default     = true
}

variable "enable_autorepair" {
  description = "Enable node auto-repair"
  type        = bool
  default     = true
}

variable "enable_autoupgrade" {
  description = "Enable node auto-upgrade"
  type        = bool
  default     = true
}

variable "preemptible" {
  description = "Use preemptible nodes"
  type        = bool
  default     = false
}

variable "oauth_scopes" {
  description = "OAuth scopes for the node pool"
  type        = list(string)
  default = [
    "https://www.googleapis.com/auth/cloud-platform"
  ]
}

variable "disk_type" {
  description = "Type of persistent disk"
  type        = string
  default     = "pd-standard"
}

variable "enable_persistent_disk" {
  description = "Enable persistent disk for applications"
  type        = bool
  default     = true
}

# Service account
variable "service_account_name" {
  description = "Service account name"
  type        = string
  default     = "adk-travel-sa"
}

# Firewall rules
variable "enable_ssh_access" {
  description = "Enable SSH access through firewall"
  type        = bool
  default     = true
}

variable "enable_http_access" {
  description = "Enable HTTP access through firewall"
  type        = bool
  default     = true
}

variable "enable_https_access" {
  description = "Enable HTTPS access through firewall"
  type        = bool
  default     = true
}

# Backup and maintenance
variable "backup_enabled" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "backup_start_time" {
  description = "Start time for backups (HH:MM)"
  type        = string
  default     = "01:00"
}

# Monitoring and alerting
variable "notification_channels" {
  description = "List of notification channels for alerts"
  type        = list(string)
  default     = []
}

variable "enable_uptime_checks" {
  description = "Enable uptime monitoring"
  type        = bool
  default     = false
}