output "public_ip_address" {
  description = "Public IP of the VM. Put this in the Jenkins VM_IP parameter."
  value       = azurerm_public_ip.public_ip.ip_address
}

output "ssh_command" {
  description = "Command to log in to the VM."
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.public_ip.ip_address}"
}

output "site_url" {
  description = "Where the website will be after the first Jenkins deploy."
  value       = "http://${azurerm_public_ip.public_ip.ip_address}/"
}
