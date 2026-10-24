variable "subscription_id" {
  description = "Azure subscription ID (run `az account show --query id -o tsv`)."
  type        = string
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "centralindia"
}

variable "prefix" {
  description = "Short name put in front of every resource name."
  type        = string
  default     = "depthub"
}

variable "vm_size" {
  description = "VM size. Standard_B1s is the cheap burstable one. If Azure says it is out of capacity in your region, try Standard_B1ms or Standard_B2s."
  type        = string
  default     = "Standard_B1s"
}

variable "image_sku" {
  description = "Ubuntu 22.04 image. \"22_04-lts-gen2\" for normal x64 sizes. Use \"22_04-lts-arm64\" only for ARM sizes (names containing 'p', like Standard_B2pts_v2)."
  type        = string
  default     = "22_04-lts-gen2"
}

variable "admin_username" {
  description = "Linux user created on the VM. Jenkins logs in as this user."
  type        = string
  default     = "azureuser"
}

variable "ssh_public_key_path" {
  description = "Path to your SSH PUBLIC key (the .pub file). Jenkins holds the matching private key."
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "ssh_alt_port" {
  description = "Extra port sshd listens on, for networks that block outgoing port 22. 443 is almost never blocked. Nothing else on the VM uses it (the website is on port 80)."
  type        = number
  default     = 443
}

variable "allowed_ssh_source" {
  description = "Who may reach port 22. \"*\" means everyone, which is needed if Jenkins runs on your laptop. Use your own IP (e.g. \"203.0.113.7/32\") if you can."
  type        = string
  default     = "*"
}
