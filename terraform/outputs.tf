output "server_ipv4" {
  description = "Public IPv4 of the provisioned server — use for the VPS_HOST GitHub secret and the api.opengrantflow.com A record."
  value       = hcloud_server.grandflow.ipv4_address
}

output "server_ipv6" {
  description = "Public IPv6 of the provisioned server."
  value       = hcloud_server.grandflow.ipv6_address
}
