resource "hcloud_ssh_key" "deploy" {
  name       = "grantflow-deploy"
  public_key = var.ssh_public_key
}

resource "hcloud_firewall" "grandflow" {
  name = "grandflow-prod"

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "22"
    # Open to everyone rather than restricted to var.allowed_ssh_cidrs: the
    # GitHub Actions deploy workflow (.github/workflows/deploy.yml) needs to
    # reach this port from GitHub's own runner infrastructure, which has no
    # stable/predictable IP range. Key-only auth (deploy user has no password
    # at all) is the actual security boundary here, not IP restriction.
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  # Everything else (Postgres/Redis/RabbitMQ/raw service ports) is implicitly
  # denied — Hetzner firewalls default-deny anything not explicitly allowed.
}

resource "hcloud_server" "grandflow" {
  name         = "grandflow-prod"
  server_type  = var.server_type
  image        = "ubuntu-24.04"
  location     = var.location
  ssh_keys     = [hcloud_ssh_key.deploy.id]
  firewall_ids = [hcloud_firewall.grandflow.id]

  user_data = templatefile("${path.module}/cloud-init.yaml", {
    ssh_public_key = var.ssh_public_key
    git_repo_url   = var.git_repo_url
  })
}
