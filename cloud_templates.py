# cloud_templates.py - Infrastructure templates for multiple cloud providers

# AWS Templates
AWS_TEMPLATES = {
    "aws_instance": """resource "aws_instance" "{name}" {{
  ami           = "{ami}"
  instance_type = "{instance_type}"
  {subnet_id_line}
  tags = {{
    Name = "{name}"
    {additional_tags}
  }}
}}
""",
    "aws_vpc": """resource "aws_vpc" "{name}" {{
  cidr_block = "{cidr_block}"
  tags = {{
    Name = "{name}"
    {additional_tags}
  }}
}}
""",
    "aws_subnet": """resource "aws_subnet" "{name}" {{
  vpc_id            = {vpc_id}
  cidr_block        = "{cidr_block}"
  availability_zone = "{az}"
  tags = {{
    Name = "{name}"
    {additional_tags}
  }}
}}
""",
    "aws_security_group": """resource "aws_security_group" "{name}" {{
  name        = "{name}"
  description = "{description}"
  vpc_id      = {vpc_id}

  {ingress}

  {egress}

  tags = {{
    Name = "{name}"
    {additional_tags}
  }}
}}
""",
    "aws_s3_bucket": """resource "aws_s3_bucket" "{name}" {{
  bucket = "{bucket_name}"
  {versioning}
  {lifecycle_rules}
  tags = {{
    Name = "{name}"
    {additional_tags}
  }}
}}
""",
    "aws_db_instance": """resource "aws_db_instance" "{name}" {{
  allocated_storage    = {storage}
  engine               = "{engine}"
  engine_version       = "{engine_version}"
  instance_class       = "{instance_class}"
  name                 = "{db_name}"
  username             = "{username}"
  password             = "{password}"
  skip_final_snapshot  = {skip_final_snapshot}
  {vpc_security_group_ids}
  {subnet_group_name}
  tags = {{
    Name = "{name}"
    {additional_tags}
  }}
}}
""",
    "aws_lambda_function": """resource "aws_lambda_function" "{name}" {{
  function_name = "{function_name}"
  role          = {role_arn}
  handler       = "{handler}"
  runtime       = "{runtime}"
  filename      = "{filename}"
  {memory_size}
  {timeout}
  {environment}
  tags = {{
    Name = "{name}"
    {additional_tags}
  }}
}}
""",
    "aws_eks_cluster": """resource "aws_eks_cluster" "{name}" {{
  name     = "{cluster_name}"
  role_arn = {role_arn}
  
  vpc_config {{
    subnet_ids = {subnet_ids}
    {security_group_ids}
  }}
  
  {encryption_config}
  {kubernetes_version}
  
  tags = {{
    Name = "{name}"
    {additional_tags}
  }}
}}
""",
    "aws_ebs_volume": """resource "aws_ebs_volume" "{name}" {{
  availability_zone = "{az}"
  size              = {size}
  {volume_type}
  {iops}
  {encrypted}
  tags = {{
    Name = "{name}"
    {additional_tags}
  }}
}}
""",
    "aws_volume_attachment": """resource "aws_volume_attachment" "{name}" {{
  device_name = "{device_name}"
  volume_id   = {volume_id}
  instance_id = {instance_id}
}}
""",
}

# Azure Templates
AZURE_TEMPLATES = {
    "azurerm_resource_group": """resource "azurerm_resource_group" "{name}" {{
  name     = "{rg_name}"
  location = "{location}"
  
  tags = {{
    {additional_tags}
  }}
}}
""",
    "azurerm_virtual_network": """resource "azurerm_virtual_network" "{name}" {{
  name                = "{vnet_name}"
  address_space       = {address_space}
  location            = "{location}"
  resource_group_name = {resource_group_name}
  
  tags = {{
    {additional_tags}
  }}
}}
""",
    "azurerm_subnet": """resource "azurerm_subnet" "{name}" {{
  name                 = "{subnet_name}"
  resource_group_name  = {resource_group_name}
  virtual_network_name = {virtual_network_name}
  address_prefixes     = {address_prefixes}
  {service_endpoints}
  {delegation}
}}
""",
    "azurerm_network_security_group": """resource "azurerm_network_security_group" "{name}" {{
  name                = "{nsg_name}"
  location            = "{location}"
  resource_group_name = {resource_group_name}
  
  {security_rules}
  
  tags = {{
    {additional_tags}
  }}
}}
""",
    "azurerm_storage_account": """resource "azurerm_storage_account" "{name}" {{
  name                     = "{storage_name}"
  resource_group_name      = {resource_group_name}
  location                 = "{location}"
  account_tier             = "{account_tier}"
  account_replication_type = "{replication_type}"
  {access_tier}
  {enable_https_traffic_only}
  
  tags = {{
    {additional_tags}
  }}
}}
""",
    "azurerm_linux_virtual_machine": """resource "azurerm_linux_virtual_machine" "{name}" {{
  name                = "{vm_name}"
  resource_group_name = {resource_group_name}
  location            = "{location}"
  size                = "{size}"
  admin_username      = "{admin_username}"
  
  network_interface_ids = {network_interface_ids}
  
  admin_ssh_key {{
    username   = "{admin_username}"
    public_key = {ssh_public_key}
  }}
  
  os_disk {{
    caching              = "ReadWrite"
    storage_account_type = "{storage_account_type}"
  }}
  
  source_image_reference {{
    publisher = "{publisher}"
    offer     = "{offer}"
    sku       = "{sku}"
    version   = "{version}"
  }}
  
  tags = {{
    {additional_tags}
  }}
}}
""",
    "azurerm_windows_virtual_machine": """resource "azurerm_windows_virtual_machine" "{name}" {{
  name                = "{vm_name}"
  resource_group_name = {resource_group_name}
  location            = "{location}"
  size                = "{size}"
  admin_username      = "{admin_username}"
  admin_password      = "{admin_password}"
  
  network_interface_ids = {network_interface_ids}
  
  os_disk {{
    caching              = "ReadWrite"
    storage_account_type = "{storage_account_type}"
  }}
  
  source_image_reference {{
    publisher = "{publisher}"
    offer     = "{offer}"
    sku       = "{sku}"
    version   = "{version}"
  }}
  
  tags = {{
    {additional_tags}
  }}
}}
""",
}

# GCP Templates
GCP_TEMPLATES = {
    "google_compute_network": """resource "google_compute_network" "{name}" {{
  name                    = "{network_name}"
  auto_create_subnetworks = {auto_create_subnetworks}
  {description}
}}
""",
    "google_compute_subnetwork": """resource "google_compute_subnetwork" "{name}" {{
  name          = "{subnetwork_name}"
  ip_cidr_range = "{ip_cidr_range}"
  region        = "{region}"
  network       = {network}
  {description}
  {secondary_ip_range}
}}
""",
    "google_compute_firewall": """resource "google_compute_firewall" "{name}" {{
  name    = "{firewall_name}"
  network = {network}
  
  {allow}
  {deny}
  
  {source_ranges}
  {source_tags}
  {target_tags}
  {description}
}}
""",
    "google_compute_instance": """resource "google_compute_instance" "{name}" {{
  name         = "{instance_name}"
  machine_type = "{machine_type}"
  zone         = "{zone}"
  
  boot_disk {{
    initialize_params {{
      image = "{image}"
      size  = "{size}"
      type  = "{type}"
    }}
  }}
  
  network_interface {{
    network = {network}
    {subnetwork}
    {access_config}
  }}
  
  {metadata}
  {tags}
  {service_account}
  {allow_stopping_for_update}
  
  {labels}
}}
""",
    "google_storage_bucket": """resource "google_storage_bucket" "{name}" {{
  name     = "{bucket_name}"
  location = "{location}"
  {storage_class}
  {versioning}
  {lifecycle_rule}
  {website}
  {cors}
  {encryption}
  {uniform_bucket_level_access}
  
  {labels}
}}
""",
    "google_sql_database_instance": """resource "google_sql_database_instance" "{name}" {{
  name             = "{instance_name}"
  database_version = "{database_version}"
  region           = "{region}"
  
  settings {{
    tier = "{tier}"
    {availability_type}
    {backup_configuration}
    {disk_size}
    {disk_type}
    {ip_configuration}
    
    {database_flags}
    {maintenance_window}
    
    {user_labels}
  }}
}}
""",
    "google_cloudfunctions_function": """resource "google_cloudfunctions_function" "{name}" {{
  name        = "{function_name}"
  description = "{description}"
  runtime     = "{runtime}"
  
  available_memory_mb   = {memory}
  source_archive_bucket = "{source_bucket}"
  source_archive_object = "{source_object}"
  trigger_http          = {trigger_http}
  entry_point           = "{entry_point}"
  
  {environment_variables}
  {vpc_connector}
  {service_account_email}
  {timeout}
  
  {labels}
}}
""",
    "google_container_cluster": """resource "google_container_cluster" "{name}" {{
  name     = "{cluster_name}"
  location = "{location}"
  
  {node_version}
  {initial_node_count}
  
  node_config {{
    {machine_type}
    {disk_size_gb}
    {oauth_scopes}
    {preemptible}
    
    {metadata}
    {tags}
    {labels}
  }}
  
  {master_auth}
  {network}
  {subnetwork}
  {ip_allocation_policy}
  {private_cluster_config}
  {logging_service}
  {monitoring_service}
  
  {resource_labels}
}}
"""
}