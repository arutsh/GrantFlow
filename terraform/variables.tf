variable "hcloud_token" {
  description = "Hetzner Cloud API token (project-scoped). Set via TF_VAR_hcloud_token env var, never committed."
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "Public half of the existing GrandFlow deploy keypair (private half is already the VPS_SSH_KEY GitHub secret)."
  type        = string
  default     = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFwx+pb2+mTW+jIVitpWIZ9ZRUvnv4mqWKQDxrDmHKrd github-actions-deploy@grantflow"
}

variable "server_type" {
  description = "Hetzner server type."
  type        = string
  default     = "cx23"
}

variable "location" {
  description = "Hetzner datacenter location."
  type        = string
  default     = "hel1"
}

variable "git_repo_url" {
  description = "Repo cloned onto the server by cloud-init at first boot."
  type        = string
  default     = "https://github.com/arutsh/GrantFlow.git"
}
