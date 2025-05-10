import json
import os
import logging
import re
from typing import Dict, List, Tuple, Optional, Any

import spacy
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv
import boto3
import uvicorn

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI-Powered IaC Generator",
    description="Generate Terraform code from natural language descriptions",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Load NLP model
try:
    nlp = spacy.load("en_core_web_lg")
    logger.info("Loaded spaCy NLP model")
except OSError:
    logger.warning("Downloading spaCy model...")
    os.system("python -m spacy download en_core_web_lg")
    nlp = spacy.load("en_core_web_lg")
    logger.info("Downloaded and loaded spaCy NLP model")

# Models
class InfrastructureRequest(BaseModel):
    description: str
    cloud_provider: str = "aws"
    region: Optional[str] = None
    include_cost_estimate: bool = False
    
class Resource(BaseModel):
    type: str
    name: str
    parameters: Dict[str, Any]
    
class InfrastructureResponse(BaseModel):
    resources: List[Resource]
    terraform_code: str
    estimated_cost: Optional[float] = None
    
# Cloud provider templates
from cloud_templates import (
    AWS_TEMPLATES, 
    AZURE_TEMPLATES, 
    GCP_TEMPLATES
)

TEMPLATES = {
    "aws": AWS_TEMPLATES,
    "azure": AZURE_TEMPLATES,
    "gcp": GCP_TEMPLATES
}

# Helper functions
def extract_entities(description: str) -> Dict[str, Any]:
    """
    Extract infrastructure entities from natural language description
    using spaCy NLP model with improved entity recognition.
    """
    doc = nlp(description.lower())
    
    # Initialize default values
    entities = {
        "resources": [],
        "region": "us-west-2",
        "environment": "dev",
        "instance_type": "t2.micro",
        "storage_size": 20,
        "vpc_cidr": "10.0.0.0/16",
        "subnet_cidr": "10.0.1.0/24",
        "count": 1,
        "availability_zones": 1,
    }
    
    # Resource types with expanded keywords for better matching
    resource_types = {
        "ec2": ["ec2", "instance", "server", "virtual machine", "vm", "compute"],
        "s3": ["s3", "bucket", "storage", "object storage", "file storage"],
        "rds": ["rds", "database", "db", "mysql", "postgres", "postgresql", "sql", "aurora"],
        "vpc": ["vpc", "network", "virtual private cloud"],
        "subnet": ["subnet", "sub-network", "sub network"],
        "security_group": ["security group", "firewall", "sg", "firewall rules", "security rules"],
        "lambda": ["lambda", "function", "serverless", "event-driven"],
        "eks": ["eks", "kubernetes", "k8s", "container", "cluster", "orchestration"],
        "ebs": ["ebs", "volume", "disk", "storage volume", "block storage"],
        "alb": ["alb", "load balancer", "elb", "application load balancer", "balancer"],
        "nat": ["nat", "nat gateway", "network address translation"],
        "cloudfront": ["cloudfront", "cdn", "content delivery", "distribution"],
        "route53": ["route53", "dns", "domain"],
        "elasticache": ["elasticache", "redis", "memcached", "cache"],
        "dynamodb": ["dynamodb", "nosql", "document database", "key-value"],
        "iam": ["iam", "role", "policy", "permission", "access"],
    }
    
    # Find resources in text
    for resource_type, keywords in resource_types.items():
        for keyword in keywords:
            if keyword in description.lower():
                entities["resources"].append(resource_type)
                break
    
    # Remove duplicates
    entities["resources"] = list(set(entities["resources"]))
    
    # Extract counts and quantities
    count_patterns = [
        (r'(\d+)\s+(instance|server|vm|ec2)', "count"),
        (r'(\d+)\s+(availability zone)', "availability_zones"),
    ]
    
    for pattern, entity_key in count_patterns:
        matches = re.findall(pattern, description.lower())
        if matches:
            entities[entity_key] = int(matches[0][0])
    
    # Extract instance types - covers all common types
    instance_patterns = [
        r't2\.(micro|small|medium|large|xlarge)',
        r't3\.(micro|small|medium|large|xlarge)',
        r't3a\.(micro|small|medium|large|xlarge)',
        r'm5\.(large|xlarge|2xlarge|4xlarge)',
        r'm6g\.(large|xlarge|2xlarge|4xlarge)',
        r'c5\.(large|xlarge|2xlarge|4xlarge)',
        r'r5\.(large|xlarge|2xlarge|4xlarge)',
    ]
    
    for pattern in instance_patterns:
        matches = re.findall(pattern, description.lower())
        if matches:
            # Extract the full match
            full_match = re.search(pattern, description.lower())
            if full_match:
                entities["instance_type"] = full_match.group(0)
    
    # Extract storage size
    storage_pattern = r'(\d+)\s*(gb|gigabyte|gigabytes|g)'
    storage_matches = re.findall(storage_pattern, description.lower())
    if storage_matches:
        entities["storage_size"] = int(storage_matches[0][0])
    
    # Extract region
    regions = {
        "us-east-1": ["us east 1", "us-east-1", "n. virginia", "north virginia", "virginia"],
        "us-east-2": ["us east 2", "us-east-2", "ohio"],
        "us-west-1": ["us west 1", "us-west-1", "california", "n. california", "north california"],
        "us-west-2": ["us west 2", "us-west-2", "oregon"],
        "eu-west-1": ["eu west 1", "eu-west-1", "ireland"],
        "eu-west-2": ["eu west 2", "eu-west-2", "london"],
        "eu-central-1": ["eu central 1", "eu-central-1", "frankfurt"],
        "ap-southeast-1": ["ap southeast 1", "ap-southeast-1", "singapore"],
        "ap-southeast-2": ["ap southeast 2", "ap-southeast-2", "sydney"],
        "ap-northeast-1": ["ap northeast 1", "ap-northeast-1", "tokyo"],
    }
    
    for region, keywords in regions.items():
        if any(keyword in description.lower() for keyword in keywords):
            entities["region"] = region
            break
    
    # Extract CIDR blocks
    cidr_pattern = r'\d+\.\d+\.\d+\.\d+/\d+'
    cidr_matches = re.findall(cidr_pattern, description)
    if cidr_matches:
        if len(cidr_matches) >= 1:
            entities["vpc_cidr"] = cidr_matches[0]
        if len(cidr_matches) >= 2:
            entities["subnet_cidr"] = cidr_matches[1]
    
    # Extract environments
    environments = ["dev", "development", "test", "testing", "staging", "prod", "production"]
    for env in environments:
        if env in description.lower():
            entities["environment"] = env
            break
    
    return entities

def parse_description(description: str, cloud_provider: str) -> List[Resource]:
    """
    Parse the description and return a list of resources with improved resource detection
    """
    entities = extract_entities(description)
    resources = []
    
    if cloud_provider == "aws":
        # Create AWS resources
        if "vpc" in entities["resources"]:
            resources.append(Resource(
                type="aws_vpc",
                name="main",
                parameters={
                    "cidr_block": entities["vpc_cidr"],
                    "tags": {
                        "Name": f"{entities['environment']}-vpc",
                        "Environment": entities["environment"],
                    }
                }
            ))
            
        if "subnet" in entities["resources"]:
            # Create subnets across availability zones if specified
            for i in range(entities["availability_zones"]):
                az_suffix = chr(97 + i)  # 'a', 'b', 'c', etc.
                # Calculate subnet CIDR - increment the third octet for each AZ
                cidr_parts = entities["subnet_cidr"].split('.')
                cidr_parts[2] = str(int(cidr_parts[2]) + i)
                subnet_cidr = '.'.join(cidr_parts)
                
                resources.append(Resource(
                    type="aws_subnet",
                    name=f"main_{az_suffix}",
                    parameters={
                        "vpc_id": "${aws_vpc.main.id}",
                        "cidr_block": subnet_cidr,
                        "availability_zone": f"{entities['region']}{az_suffix}",
                        "tags": {
                            "Name": f"{entities['environment']}-subnet-{az_suffix}",
                            "Environment": entities["environment"],
                        }
                    }
                ))
            
        if "ec2" in entities["resources"]:
            # Get appropriate AMI for the region
            ami_map = {
                "us-east-1": "ami-0c55b159cbfafe1f0",
                "us-east-2": "ami-0ebc8f6f580a04647",
                "us-west-1": "ami-0cf6f5c8a62fa5da6",
                "us-west-2": "ami-0841edc20334f9287",
                "eu-west-1": "ami-0a8e758f5e873d1c1",
                "eu-west-2": "ami-0596aab74c9968917",
                "eu-central-1": "ami-0db9040eb3ab74509",
                "ap-southeast-1": "ami-0f515c764b6e92553",
                "ap-southeast-2": "ami-05654c5823f5a5efc",
                "ap-northeast-1": "ami-0df22986b9bdade7a",
            }
            ami = ami_map.get(entities["region"], ami_map["us-west-2"])
            
            # Create multiple instances if requested
            for i in range(entities["count"]):
                suffix = f"_{i+1}" if entities["count"] > 1 else ""
                resources.append(Resource(
                    type="aws_instance",
                    name=f"app_server{suffix}",
                    parameters={
                        "ami": ami,
                        "instance_type": entities["instance_type"],
                        "subnet_id": "${aws_subnet.main_a.id}" if "subnet" in entities["resources"] else None,
                        "vpc_security_group_ids": ["${aws_security_group.app.id}"] if "security_group" in entities["resources"] else None,
                        "tags": {
                            "Name": f"{entities['environment']}-app-server{suffix}",
                            "Environment": entities["environment"],
                        }
                    }
                ))
            
        if "security_group" in entities["resources"]:
            resources.append(Resource(
                type="aws_security_group",
                name="app",
                parameters={
                    "name": f"{entities['environment']}-app-sg",
                    "description": "Allow necessary application traffic",
                    "vpc_id": "${aws_vpc.main.id}" if "vpc" in entities["resources"] else None,
                    "ingress": [
                        {
                            "from_port": 80,
                            "to_port": 80,
                            "protocol": "tcp",
                            "cidr_blocks": ["0.0.0.0/0"],
                            "description": "HTTP"
                        },
                        {
                            "from_port": 443,
                            "to_port": 443,
                            "protocol": "tcp",
                            "cidr_blocks": ["0.0.0.0/0"],
                            "description": "HTTPS"
                        },
                        {
                            "from_port": 22,
                            "to_port": 22,
                            "protocol": "tcp",
                            "cidr_blocks": ["0.0.0.0/0"],
                            "description": "SSH"
                        }
                    ],
                    "egress": [
                        {
                            "from_port": 0,
                            "to_port": 0,
                            "protocol": "-1",
                            "cidr_blocks": ["0.0.0.0/0"],
                            "description": "Allow all outbound traffic"
                        }
                    ],
                    "tags": {
                        "Name": f"{entities['environment']}-app-sg",
                        "Environment": entities["environment"],
                    }
                }
            ))
            
        if "ebs" in entities["resources"]:
            resources.append(Resource(
                type="aws_ebs_volume",
                name="data",
                parameters={
                    "availability_zone": f"{entities['region']}a",
                    "size": entities["storage_size"],
                    "encrypted": True,
                    "tags": {
                        "Name": f"{entities['environment']}-data-volume",
                        "Environment": entities["environment"],
                    }
                }
            ))
            
            if "ec2" in entities["resources"]:
                resources.append(Resource(
                    type="aws_volume_attachment",
                    name="app_data",
                    parameters={
                        "device_name": "/dev/sdh",
                        "volume_id": "${aws_ebs_volume.data.id}",
                        "instance_id": "${aws_instance.app_server.id}"
                    }
                ))
            
        if "s3" in entities["resources"]:
            resources.append(Resource(
                type="aws_s3_bucket",
                name="data",
                parameters={
                    "bucket_prefix": f"{entities['environment']}-data-",
                    "versioning": {
                        "enabled": True
                    },
                    "tags": {
                        "Environment": entities["environment"],
                    }
                }
            ))
            
        if "rds" in entities["resources"]:
            resources.append(Resource(
                type="aws_db_instance",
                name="database",
                parameters={
                    "allocated_storage": entities["storage_size"],
                    "engine": "mysql",
                    "engine_version": "8.0",
                    "instance_class": "db.t3.micro",
                    "name": "mydb",
                    "username": "admin",
                    "password": "change_me_in_production",  # This should be handled securely
                    "skip_final_snapshot": True,
                    "deletion_protection": False,  # Enable in production
                    "storage_encrypted": True,
                    "tags": {
                        "Environment": entities["environment"],
                    }
                }
            ))
            
        if "alb" in entities["resources"] or "load balancer" in description.lower():
            resources.append(Resource(
                type="aws_lb",
                name="app",
                parameters={
                    "name": f"{entities['environment']}-app-lb",
                    "internal": False,
                    "load_balancer_type": "application",
                    "security_groups": ["${aws_security_group.app.id}"] if "security_group" in entities["resources"] else None,
                    "subnets": [
                        "${aws_subnet.main_a.id}",
                        "${aws_subnet.main_b.id}" if entities["availability_zones"] > 1 else "${aws_subnet.main_a.id}"
                    ] if "subnet" in entities["resources"] else None,
                    "enable_deletion_protection": False,
                    "tags": {
                        "Environment": entities["environment"],
                    }
                }
            ))
            
            # Add target group for the ALB
            resources.append(Resource(
                type="aws_lb_target_group",
                name="app",
                parameters={
                    "name": f"{entities['environment']}-app-tg",
                    "port": 80,
                    "protocol": "HTTP",
                    "vpc_id": "${aws_vpc.main.id}" if "vpc" in entities["resources"] else None,
                    "health_check": {
                        "enabled": True,
                        "path": "/",
                        "port": "traffic-port",
                        "protocol": "HTTP",
                        "healthy_threshold": 3,
                        "unhealthy_threshold": 3,
                        "timeout": 5,
                        "interval": 30,
                        "matcher": "200"
                    },
                    "tags": {
                        "Environment": entities["environment"],
                    }
                }
            ))
            
            # Add listener for the ALB
            resources.append(Resource(
                type="aws_lb_listener",
                name="app_http",
                parameters={
                    "load_balancer_arn": "${aws_lb.app.arn}",
                    "port": 80,
                    "protocol": "HTTP",
                    "default_action": {
                        "type": "forward",
                        "target_group_arn": "${aws_lb_target_group.app.arn}"
                    }
                }
            ))
            
        if "elasticache" in entities["resources"] or "redis" in description.lower():
            resources.append(Resource(
                type="aws_elasticache_cluster",
                name="redis",
                parameters={
                    "cluster_id": f"{entities['environment']}-redis",
                    "engine": "redis",
                    "node_type": "cache.t3.micro",
                    "num_cache_nodes": 1,
                    "parameter_group_name": "default.redis6.x",
                    "engine_version": "6.x",
                    "port": 6379,
                    "subnet_group_name": "${aws_elasticache_subnet_group.default.name}" if "subnet" in entities["resources"] else None,
                    "security_group_ids": ["${aws_security_group.redis.id}"],
                    "tags": {
                        "Environment": entities["environment"],
                    }
                }
            ))
            
            if "subnet" in entities["resources"]:
                resources.append(Resource(
                    type="aws_elasticache_subnet_group",
                    name="default",
                    parameters={
                        "name": f"{entities['environment']}-redis-subnet-group",
                        "subnet_ids": ["${aws_subnet.main_a.id}", "${aws_subnet.main_b.id}" if entities["availability_zones"] > 1 else "${aws_subnet.main_a.id}"],
                        "description": "ElastiCache subnet group"
                    }
                ))
            
            # Security group for Redis
            resources.append(Resource(
                type="aws_security_group",
                name="redis",
                parameters={
                    "name": f"{entities['environment']}-redis-sg",
                    "description": "Allow Redis traffic",
                    "vpc_id": "${aws_vpc.main.id}" if "vpc" in entities["resources"] else None,
                    "ingress": [
                        {
                            "from_port": 6379,
                            "to_port": 6379,
                            "protocol": "tcp",
                            "security_groups": ["${aws_security_group.app.id}"] if "security_group" in entities["resources"] else None,
                            "cidr_blocks": [] if "security_group" in entities["resources"] else ["10.0.0.0/8"],
                            "description": "Redis from app servers"
                        }
                    ],
                    "egress": [
                        {
                            "from_port": 0,
                            "to_port": 0,
                            "protocol": "-1",
                            "cidr_blocks": ["0.0.0.0/0"],
                            "description": "Allow all outbound traffic"
                        }
                    ],
                    "tags": {
                        "Name": f"{entities['environment']}-redis-sg",
                        "Environment": entities["environment"],
                    }
                }
            ))
        
    elif cloud_provider == "azure":
        # Create resource group
        resources.append(Resource(
            type="azurerm_resource_group",
            name="main",
            parameters={
                "name": f"{entities['environment']}-resources",
                "location": "West US 2",  # Default to West US 2
                "tags": {
                    "Environment": entities["environment"],
                }
            }
        ))
        
        # Create Azure resources similar to AWS
        if "vpc" in entities["resources"]:
            resources.append(Resource(
                type="azurerm_virtual_network",
                name="main",
                parameters={
                    "name": f"{entities['environment']}-vnet",
                    "address_space": [entities["vpc_cidr"]],
                    "location": "${azurerm_resource_group.main.location}",
                    "resource_group_name": "${azurerm_resource_group.main.name}",
                    "tags": {
                        "Environment": entities["environment"],
                    }
                }
            ))
            
        if "subnet" in entities["resources"]:
            resources.append(Resource(
                type="azurerm_subnet",
                name="main",
                parameters={
                    "name": f"{entities['environment']}-subnet",
                    "resource_group_name": "${azurerm_resource_group.main.name}",
                    "virtual_network_name": "${azurerm_virtual_network.main.name}",
                    "address_prefixes": [entities["subnet_cidr"]],
                }
            ))
    
    elif cloud_provider == "gcp":
        # Create a Google Cloud project
        resources.append(Resource(
            type="google_project",
            name="project",
            parameters={
                "name": f"{entities['environment']}-project",
                "project_id": f"{entities['environment']}-project-id",
                "auto_create_network": True
            }
        ))
        
        # Create GCP resources
        if "vpc" in entities["resources"]:
            resources.append(Resource(
                type="google_compute_network",
                name="vpc_network",
                parameters={
                    "name": f"{entities['environment']}-network",
                    "auto_create_subnetworks": False,
                }
            ))
    
    # Clean up parameters by removing None values
    for resource in resources:
        resource.parameters = {k: v for k, v in resource.parameters.items() if v is not None}
    
    return resources

def _get_resource_count(name: str) -> int:
    """Helper function to get resource count from name"""
    if "_" not in name:
        return 1
    
    # Try to extract a number from the name (for resources like app_server_1, app_server_2)
    try:
        return int(name.split("_")[-1]) if name.split("_")[-1].isdigit() else 1
    except (ValueError, IndexError):
        return 1

def estimate_cost(resources: List[Resource], cloud_provider: str) -> float:
    """
    Provide a more accurate estimate of the monthly cost of the infrastructure
    """
    # Updated pricing data based on actual cloud provider pricing
    total_cost = 0.0
    
    cost_map = {
        "aws": {
            "aws_instance": {
                "t2.micro": 8.5, 
                "t2.small": 17.0, 
                "t2.medium": 34.0,
                "t3.nano": 3.8, 
                "t3.micro": 7.6, 
                "t3.small": 15.2, 
                "t3.medium": 30.4,
                "m5.large": 70.0, 
                "m5.xlarge": 140.0, 
                "m5.2xlarge": 280.0,
                "c5.large": 76.0, 
                "c5.xlarge": 152.0,
                "r5.large": 114.0, 
                "r5.xlarge": 228.0
            },
            "aws_ebs_volume": 0.1,  # per GB
            "aws_s3_bucket": 0.023,  # per GB, assuming 100GB for estimation
            "aws_db_instance": {
                "db.t3.micro": 12.5,
                "db.t3.small": 25.0,
                "db.t3.medium": 50.0,
                "db.m5.large": 160.0
            },
            "aws_elasticache_cluster": {
                "cache.t3.micro": 12.5,
                "cache.t3.small": 25.0,
                "cache.m5.large": 102.0
            },
            "aws_lb": 25.0,  # Base cost for ALB
            "aws_cloudfront_distribution": 50.0,  # Base cost for CloudFront
        },
        "azure": {
            "azurerm_linux_virtual_machine": {
                "Standard_B1s": 8.8, 
                "Standard_B2s": 35.0, 
                "Standard_D2s_v3": 70.0
            },
            "azurerm_storage_account": 0.02,  # per GB
            "azurerm_mysql_server": {
                "GP_Gen5_2": 75.0,
                "GP_Gen5_4": 150.0
            }
        },
        "gcp": {
            "google_compute_instance": {
                "e2-micro": 6.7, 
                "e2-small": 13.4, 
                "e2-medium": 26.8,
                "n1-standard-1": 25.0, 
                "n1-standard-2": 50.0
            },
            "google_storage_bucket": 0.02,  # per GB
            "google_sql_database_instance": {
                "db-f1-micro": 9.0,
                "db-g1-small": 30.0
            }
        }
    }
    
    # Track instance count for load balancer cost calculation
    instance_count = 1
    
    for resource in resources:
        if cloud_provider == "aws":
            if resource.type == "aws_instance":
                instance_type = resource.parameters.get("instance_type", "t2.micro")
                count = _get_resource_count(resource.name)
                total_cost += cost_map["aws"]["aws_instance"].get(instance_type, 10.0) * count
                instance_count = max(instance_count, count)
                
            elif resource.type == "aws_ebs_volume":
                size = resource.parameters.get("size", 20)
                total_cost += cost_map["aws"]["aws_ebs_volume"] * size
                
            elif resource.type == "aws_s3_bucket":
                # Assume 100GB storage as a baseline
                total_cost += cost_map["aws"]["aws_s3_bucket"] * 100
                
            elif resource.type == "aws_db_instance":
                instance_class = resource.parameters.get("instance_class", "db.t3.micro")
                storage = resource.parameters.get("allocated_storage", 20)
                total_cost += cost_map["aws"]["aws_db_instance"].get(instance_class, 15.0)
                total_cost += cost_map["aws"]["aws_ebs_volume"] * storage  # Add storage cost
                
            elif resource.type == "aws_elasticache_cluster":
                node_type = resource.parameters.get("node_type", "cache.t3.micro")
                nodes = resource.parameters.get("num_cache_nodes", 1)
                total_cost += cost_map["aws"]["aws_elasticache_cluster"].get(node_type, 12.5) * nodes
                
            elif resource.type == "aws_lb":
                total_cost += cost_map["aws"]["aws_lb"]  # Base cost
                total_cost += 10.0 * instance_count  # Add per-instance cost
                
            elif resource.type == "aws_cloudfront_distribution":
                total_cost += cost_map["aws"]["aws_cloudfront_distribution"]  # Base cost
                # Add estimated data transfer cost (10TB per month at $0.085 per GB)
                total_cost += 10 * 1024 * 0.085
                
        elif cloud_provider == "azure":
            if resource.type == "azurerm_linux_virtual_machine" or resource.type == "azurerm_windows_virtual_machine":
                size = resource.parameters.get("size", "Standard_B1s")
                total_cost += cost_map["azure"]["azurerm_linux_virtual_machine"].get(size, 10.0)
                
            elif resource.type == "azurerm_storage_account":
                # Assume 100GB storage as a baseline
                total_cost += cost_map["azure"]["azurerm_storage_account"] * 100
                
            elif resource.type == "azurerm_mysql_server":
                sku_name = resource.parameters.get("sku_name", "GP_Gen5_2")
                storage_mb = resource.parameters.get("storage_mb", 5120) / 1024  # Convert to GB
                total_cost += cost_map["azure"]["azurerm_mysql_server"].get(sku_name, 75.0)
                total_cost += cost_map["azure"]["azurerm_storage_account"] * storage_mb
                
        elif cloud_provider == "gcp":
            if resource.type == "google_compute_instance":
                machine_type = resource.parameters.get("machine_type", "e2-micro")
                machine_type = machine_type.split("/")[-1]  # Extract the machine type from the full path
                total_cost += cost_map["gcp"]["google_compute_instance"].get(machine_type, 10.0)
                
            elif resource.type == "google_storage_bucket":
                # Assume 100GB storage as a baseline
                total_cost += cost_map["gcp"]["google_storage_bucket"] * 100
                
            elif resource.type == "google_sql_database_instance":
                tier = resource.parameters.get("tier", "db-f1-micro")
                total_cost += cost_map["gcp"]["google_sql_database_instance"].get(tier, 9.0)
                
    # Add a bandwidth cost estimate (inbound + outbound)
    bandwidth_cost = 20.0
    
    return total_cost + bandwidth_cost

def generate_terraform_code(resources: List[Resource], cloud_provider: str) -> str:
    """
    Generate Terraform code from resource list with improved formatting
    """
    provider_map = {
        "aws": "aws",
        "azure": "azurerm",
        "gcp": "google"
    }
    
    # Start with provider and terraform block
    region_map = {
        "aws": "us-west-2",  # Default region
        "azure": "West US 2",
        "gcp": "us-west1"
    }
    
    # Try to find the region from the resources
    region = region_map[cloud_provider]
    for resource in resources:
        if cloud_provider == "aws" and resource.type == "aws_instance":
            # Extract region from AZ if present (e.g., us-west-2a -> us-west-2)
            az = resource.parameters.get("availability_zone", "")
            if az and az[:-1]:  # Remove the last character (zone identifier)
                region = az[:-1]
                break
    
    tf_code = f"""terraform {{
  required_providers {{
    {provider_map[cloud_provider]} = {{
      source  = "hashicorp/{provider_map[cloud_provider]}"
      version = "~> 4.0"
    }}
  }}
}}

provider "{provider_map[cloud_provider]}" {{
  region = "{region}"
}}

"""
    
    # Add each resource
    for resource in resources:
        # Convert parameters to HCL format
        params_str = ""
        for key, value in resource.parameters.items():
            if isinstance(value, dict):
                params_str += f"  {key} = {{\n"
                for k, v in value.items():
                    if isinstance(v, str):
                        params_str += f"    {k} = \"{v}\"\n"
                    else:
                        params_str += f"    {k} = {v}\n"
                params_str += "  }\n"
            elif isinstance(value, list):
                # Handle lists with different types
                if all(isinstance(item, str) for item in value):
                    # Format list of strings
                    items_str = ", ".join([f'"{item}"' for item in value])
                    params_str += f"  {key} = [{items_str}]\n"
                elif all(isinstance(item, dict) for item in value):
                    # Format list of objects (like ingress rules)
                    params_str += f"  {key} = [\n"
                    for item in value:
                        params_str += "    {\n"
                        for item_key, item_value in item.items():
                            if isinstance(item_value, str):
                                params_str += f"      {item_key} = \"{item_value}\"\n"
                            elif isinstance(item_value, list):
                                # Handle nested lists (like cidr_blocks)
                                if all(isinstance(nested_item, str) for nested_item in item_value):
                                    nested_items_str = ", ".join([f'"{nested_item}"' for nested_item in item_value])
                                    params_str += f"      {item_key} = [{nested_items_str}]\n"
                                else:
                                    params_str += f"      {item_key} = {json.dumps(item_value)}\n"
                            else:
                                params_str += f"      {item_key} = {item_value}\n"
                        params_str += "    },\n"
                    params_str += "  ]\n"
                else:
                    # Use JSON for mixed lists
                    params_str += f"  {key} = {json.dumps(value)}\n"
            elif isinstance(value, str) and "${" in value:
                # Reference to another resource, don't quote
                params_str += f"  {key} = {value}\n"
            elif isinstance(value, str):
                params_str += f"  {key} = \"{value}\"\n"
            elif isinstance(value, bool):
                params_str += f"  {key} = {str(value).lower()}\n"
            else:
                params_str += f"  {key} = {value}\n"
        
        # Add the resource block
        tf_code += f"""resource "{resource.type}" "{resource.name}" {{
{params_str}}}

"""
    
    return tf_code

def validate_terraform(tf_code: str) -> Tuple[bool, str]:
    """
    Validate the generated Terraform code with improved error checking
    """
    # Check for common syntax issues
    # 1. Missing closing braces
    opening_braces = tf_code.count("{")
    closing_braces = tf_code.count("}")
    if opening_braces != closing_braces:
        return False, f"Syntax error: Mismatched braces ({opening_braces} opening, {closing_braces} closing)"
    
    # 2. Check for required provider block
    if "required_providers" not in tf_code:
        return False, "Missing required_providers block"
    
    # 3. Check for provider configuration
    if "provider" not in tf_code:
        return False, "Missing provider configuration"
    
    # 4. Check for resources
    if "resource" not in tf_code:
        return False, "No resources defined in Terraform code"
    
    # 5. Check for invalid reference syntax
    invalid_refs = re.findall(r'\${[^}]*?{', tf_code)
    if invalid_refs:
        return False, f"Invalid reference syntax: Nested curly braces in references"
    
    return True, "Terraform code appears valid"

# API routes
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate")
async def generate_infrastructure(req: InfrastructureRequest):
    """
    Generate Terraform code from natural language description
    """
    try:
        logger.info(f"Processing request for: {req.description}")
        
        # Parse the description into resources
        resources = parse_description(req.description, req.cloud_provider)
        
        # Generate Terraform code
        tf_code = generate_terraform_code(resources, req.cloud_provider)
        
        # Validate the code
        is_valid, validation_message = validate_terraform(tf_code)
        if not is_valid:
            raise HTTPException(status_code=400, detail=validation_message)
        
        # Estimate cost if requested
        estimated_cost = None
        if req.include_cost_estimate:
            estimated_cost = estimate_cost(resources, req.cloud_provider)
        
        response = InfrastructureResponse(
            resources=[resource.dict() for resource in resources],
            terraform_code=tf_code,
            estimated_cost=estimated_cost
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error generating infrastructure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-html", response_class=HTMLResponse)
async def generate_html(
    request: Request,
    description: str = Form(...),
    cloud_provider: str = Form("aws"),
    include_cost_estimate: bool = Form(False)
):
    """
    Generate Terraform code and return HTML response
    """
    try:
        # Create a request object
        req = InfrastructureRequest(
            description=description,
            cloud_provider=cloud_provider,
            include_cost_estimate=include_cost_estimate
        )
        
        # Use the same logic as the API endpoint
        resources = parse_description(req.description, req.cloud_provider)
        tf_code = generate_terraform_code(resources, req.cloud_provider)
        
        # Estimate cost if requested
        estimated_cost = None
        if req.include_cost_estimate:
            estimated_cost = estimate_cost(resources, req.cloud_provider)
        
        return templates.TemplateResponse(
            "result.html", 
            {
                "request": request, 
                "tf_code": tf_code,
                "resources": resources,
                "estimated_cost": estimated_cost
            }
        )
    
    except Exception as e:
        logger.error(f"Error generating infrastructure: {str(e)}")
        return templates.TemplateResponse(
            "error.html", 
            {
                "request": request, 
                "error": str(e)
            }
        )

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)