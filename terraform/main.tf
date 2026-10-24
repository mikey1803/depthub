# DeptHub infrastructure on Azure.
# Everything here is created with `terraform apply` and removed with `terraform destroy`.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.81" # any 4.x from 4.81 up; 4.x needs subscription_id (set below)
    }
  }
}

# Since azurerm 4.0 the provider needs to know which subscription to use.
provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

# Resource Group: a folder that holds every resource below.
# Deleting it deletes everything inside, which is how `terraform destroy` stays clean.
resource "azurerm_resource_group" "rg" {
  name     = "${var.prefix}-rg"
  location = var.location
}

# Virtual Network: our private network in Azure.
resource "azurerm_virtual_network" "vnet" {
  name                = "${var.prefix}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

# Subnet: a smaller slice of the virtual network where the VM lives.
resource "azurerm_subnet" "subnet" {
  name                 = "${var.prefix}-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

# Network Security Group: the firewall. Only SSH (22) and HTTP (80) may come in.
resource "azurerm_network_security_group" "nsg" {
  name                = "${var.prefix}-nsg"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  # Port 22: Jenkins and you connect here over SSH.
  security_rule {
    name                       = "allow-ssh"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = var.allowed_ssh_source
    destination_address_prefix = "*"
  }

  # Second SSH port (443). Many college and office networks block outgoing port 22,
  # but allow 443. cloud-init makes sshd listen on both ports, with the same key-only login.
  security_rule {
    name                       = "allow-ssh-alt"
    priority                   = 105
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = tostring(var.ssh_alt_port)
    source_address_prefix      = var.allowed_ssh_source
    destination_address_prefix = "*"
  }

  # Port 80: visitors open the website here.
  security_rule {
    name                       = "allow-http"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# Public IP: the address the outside world uses to reach the VM.
# Standard SKU only supports Static addresses, so the IP will not change on reboot.
resource "azurerm_public_ip" "public_ip" {
  name                = "${var.prefix}-ip"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

# Network Interface: the VM's network card. It joins the subnet and gets the public IP.
resource "azurerm_network_interface" "nic" {
  name                = "${var.prefix}-nic"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.public_ip.id
  }
}

# Attach the firewall rules to the network card.
resource "azurerm_network_interface_security_group_association" "nic_nsg" {
  network_interface_id      = azurerm_network_interface.nic.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

# The Linux VM: Ubuntu 22.04, logs in with an SSH key (no password).
resource "azurerm_linux_virtual_machine" "vm" {
  name                = "${var.prefix}-vm"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  size                = var.vm_size
  admin_username      = var.admin_username

  network_interface_ids = [azurerm_network_interface.nic.id]

  disable_password_authentication = true

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(pathexpand(var.ssh_public_key_path))
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = var.image_sku
    version   = "latest"
  }

  # cloud-init runs once on first boot: installs nginx + python and prepares /opt/depthub.
  custom_data = base64encode(templatefile("${path.module}/cloud-init.yaml", {
    admin_username = var.admin_username
    ssh_alt_port   = var.ssh_alt_port
  }))
}
