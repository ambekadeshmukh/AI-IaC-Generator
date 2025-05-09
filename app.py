import json
import os
import logging
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
    using spaCy NLP model with custom entity recognition.
    """
    doc = nlp(description)
    
    # Initialize default values
    entities = {
        "resources": [],
        "region": "us-west-2",
        "environment": "dev",
        "instance_type": "t2.micro",
        "storage_size": 20,
        "vpc_cidr": "10.0.0.0/16",
        "subnet_cidr": "10.0.1.0/24"
    }
    
    # Extract entities: This is simplified - in production, use a trained NER model
    resource_types = {
        "ec2": ["ec2", "instance", "server", "virtual machine", "vm"],
        "s3": ["s3", "bucket", "storage", "object storage"],
        "rds": ["rds", "database", "db", "mysql", "postgres", "sql"],
        "vpc": ["vpc", "network", "virtual private cloud"],
        "subnet": ["subnet", "sub-network"],
        "security_group": ["security group", "firewall", "sg"],
        "lambda": ["lambda", "function", "serverless"],
        "eks": ["eks", "kubernetes", "k8s", "container"],
        "ebs": ["ebs", "volume", "disk", "storage volume"],
    }
    
    # Find resources in text
    for resource_type, keywords in resource_types.items():
        for keyword in keywords:
            if keyword in description.lower():
                entities["resources"].append(resource_type)
                break
    
    # Remove duplicates
    entities["resources"] = list(set(entities["resources"]))
    
    # Extract quantities
    for token in doc:
        if token.like_num:
            if "gb" in token.nbor().text.lower() or "gigabyte" in token.nbor().text.lower():
                entities["storage_size"] = int(token.text)
            if any(instance_type in (token.text + token.nbor().text).lower() 
                  for instance_type in ["t2.", "t3.", "m5."]):
                entities["instance_type"] = (token.text + token.nbor().text).lower()
    
    # Extract region
    regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
    for region in regions:
        if region in description:
            entities["region"] = region
            break
    
    # Extract CIDR blocks
    import re
    cidr_pattern = r'\d+\.\d+\.\d+\.\d+/\d+'
    cidr_matches = re.findall(cidr_pattern, description)
    if cidr_matches:
        if len(cidr_matches) >= 1:
            entities["vpc_cidr"] = cidr_matches[0]
        if len(cidr_matches) >= 2:
            entities["subnet_cidr"] = cidr_matches[1]
    
    return entities

def parse_description(description: str, cloud_provider: str) -> List[Resource]:
    """
    Parse the description and return a list of resources
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
            resources.append(Resource(
                type="aws_subnet",
                name="main",
                parameters={
                    "vpc_id": "${aws_vpc.main.id}",
                    "cidr_block": entities["subnet_cidr"],
                    "availability_zone": f"{entities['region']}a",
                    "tags": {
                        "Name": f"{entities['environment']}-subnet",
                        "Environment": entities["environment"],
                    }
                }
            ))
            
        if "ec2" in entities["resources"]:
            resources.append(Resource(
                type="aws_instance",
                name="app_server",
                parameters={
                    "ami": "ami-0c55b159cbfafe1f0",  # This should be dynamically fetched based on region
                    "instance_type": entities["instance_type"],
                    "subnet_id": "${aws_subnet.main.id}" if "subnet" in entities["resources"] else None,
                    "tags": {
                        "Name": f"{entities['environment']}-app-server",
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
                    "tags": {
                        "Name": f"{entities['environment']}-data-volume",
                        "Environment": entities["environment"],
                    }
                }
            ))
            
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
                    "tags": {
                        "Environment": entities["environment"],
                    }
                }
            ))
            
    elif cloud_provider == "azure":
        # Create Azure resources (simplified)
        if "vpc" in entities["resources"]:
            resources.append(Resource(
                type="azurerm_virtual_network",
                name="main",
                parameters={
                    "address_space": [entities["vpc_cidr"]],
                    "location": "West Europe",  # Map AWS regions to Azure regions
                    "resource_group_name": "${azurerm_resource_group.main.name}",
                }
            ))
    
    elif cloud_provider == "gcp":
        # Create GCP resources (simplified)
        if "vpc" in entities["resources"]:
            resources.append(Resource(
                type="google_compute_network",
                name="vpc_network",
                parameters={
                    "name": "terraform-network",
                    "auto_create_subnetworks": False,
                }
            ))
    
    # Clean up parameters by removing None values
    for resource in resources:
        resource.parameters = {k: v for k, v in resource.parameters.items() if v is not None}
    
    return resources

def generate_terraform_code(resources: List[Resource], cloud_provider: str) -> str:
    """
    Generate Terraform code from resource list
    """
    provider_map = {
        "aws": "aws",
        "azure": "azurerm",
        "gcp": "google"
    }
    
    # Start with provider and terraform block
    tf_code = f"""terraform {{
  required_providers {{
    {provider_map[cloud_provider]} = {{
      source  = "hashicorp/{provider_map[cloud_provider]}"
      version = "~> 4.0"
    }}
  }}
}}

provider "{provider_map[cloud_provider]}" {{
  region = "us-west-2"  # This should be parameterized
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

def estimate_cost(resources: List[Resource], cloud_provider: str) -> float:
    """
    Provide a rough estimate of the monthly cost of the infrastructure
    
    This is a simplified function that would need to be replaced with 
    actual API calls to cloud pricing APIs or cost calculators
    """
    # Simplified cost estimation
    total_cost = 0.0
    
    cost_map = {
        "aws": {
            "aws_instance": {"t2.micro": 8.5, "t3.nano": 3.8, "m5.large": 70},
            "aws_ebs_volume": 0.1,  # per GB
            "aws_s3_bucket": 0.023,  # per GB
            "aws_db_instance": 15,  # base cost
        },
        "azure": {
            "azurerm_virtual_machine": {"Standard_B1s": 8.8, "Standard_D2s_v3": 70},
            "azurerm_storage_account": 0.02,  # per GB
        },
        "gcp": {
            "google_compute_instance": {"e2-micro": 6.7, "n1-standard-1": 25},
            "google_storage_bucket": 0.02,  # per GB
        }
    }
    
    for resource in resources:
        if cloud_provider == "aws":
            if resource.type == "aws_instance":
                instance_type = resource.parameters.get("instance_type", "t2.micro")
                total_cost += cost_map["aws"]["aws_instance"].get(instance_type, 10)
            elif resource.type == "aws_ebs_volume":
                size = resource.parameters.get("size", 1)
                total_cost += cost_map["aws"]["aws_ebs_volume"] * size
            elif resource.type == "aws_s3_bucket":
                # Assume 10GB storage for estimation
                total_cost += cost_map["aws"]["aws_s3_bucket"] * 10
            elif resource.type == "aws_db_instance":
                total_cost += cost_map["aws"]["aws_db_instance"]
        # Similar logic for Azure and GCP
    
    return total_cost

def validate_terraform(tf_code: str) -> Tuple[bool, str]:
    """
    Validate the generated Terraform code
    """
    # This would typically call 'terraform validate' or a validation library
    # For now, we just do a basic check
    if "resource" not in tf_code:
        return False, "No resources defined in Terraform code"
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