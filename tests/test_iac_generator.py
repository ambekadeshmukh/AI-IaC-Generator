import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app import app, extract_entities, parse_description, generate_terraform_code, estimate_cost, validate_terraform

client = TestClient(app)

# Sample test data
SAMPLE_DESCRIPTION = "Create an EC2 instance with a security group and an S3 bucket"
SAMPLE_RESOURCES = [
    {
        "type": "aws_instance",
        "name": "app_server",
        "parameters": {
            "ami": "ami-0c55b159cbfafe1f0",
            "instance_type": "t2.micro",
            "tags": {
                "Name": "dev-app-server",
                "Environment": "dev",
            }
        }
    },
    {
        "type": "aws_security_group",
        "name": "app_sg",
        "parameters": {
            "name": "app-sg",
            "description": "Allow HTTP and SSH traffic",
            "vpc_id": "${aws_vpc.main.id}",
            "ingress": [
                {
                    "from_port": 80,
                    "to_port": 80,
                    "protocol": "tcp",
                    "cidr_blocks": ["0.0.0.0/0"]
                },
                {
                    "from_port": 22,
                    "to_port": 22,
                    "protocol": "tcp",
                    "cidr_blocks": ["0.0.0.0/0"]
                }
            ],
            "egress": [
                {
                    "from_port": 0,
                    "to_port": 0,
                    "protocol": "-1",
                    "cidr_blocks": ["0.0.0.0/0"]
                }
            ],
            "tags": {
                "Name": "app-sg",
                "Environment": "dev"
            }
        }
    },
    {
        "type": "aws_s3_bucket",
        "name": "data",
        "parameters": {
            "bucket_prefix": "dev-data-",
            "tags": {
                "Environment": "dev",
            }
        }
    }
]

# Test the extract_entities function
def test_extract_entities():
    # Test basic extraction
    entities = extract_entities(SAMPLE_DESCRIPTION)
    assert "resources" in entities
    assert isinstance(entities["resources"], list)
    assert "ec2" in entities["resources"]
    assert "s3" in entities["resources"]
    
    # Test extraction with specific parameters
    detailed_description = "Create a t3.large EC2 instance in us-east-1 with a 100GB EBS volume"
    entities = extract_entities(detailed_description)
    assert "ec2" in entities["resources"]
    assert "ebs" in entities["resources"]
    assert entities["instance_type"] == "t3.large"
    assert entities["region"] == "us-east-1"
    assert entities["storage_size"] == 100
    
    # Test CIDR extraction
    cidr_description = "Create a VPC with CIDR 192.168.0.0/16 and a subnet with CIDR 192.168.1.0/24"
    entities = extract_entities(cidr_description)
    assert "vpc" in entities["resources"]
    assert "subnet" in entities["resources"]
    assert entities["vpc_cidr"] == "192.168.0.0/16"
    assert entities["subnet_cidr"] == "192.168.1.0/24"

# Test the parse_description function
def test_parse_description():
    # Mock the extract_entities function
    with patch('app.extract_entities') as mock_extract:
        mock_extract.return_value = {
            "resources": ["ec2", "s3"],
            "region": "us-west-2",
            "environment": "dev",
            "instance_type": "t2.micro",
            "storage_size": 20,
            "vpc_cidr": "10.0.0.0/16",
            "subnet_cidr": "10.0.1.0/24"
        }
        
        resources = parse_description(SAMPLE_DESCRIPTION, "aws")
        assert len(resources) >= 2
        
        # Check if ec2 instance is in resources
        ec2_resources = [r for r in resources if r.type == "aws_instance"]
        assert len(ec2_resources) > 0
        assert ec2_resources[0].parameters["instance_type"] == "t2.micro"
        
        # Check if s3 bucket is in resources
        s3_resources = [r for r in resources if r.type == "aws_s3_bucket"]
        assert len(s3_resources) > 0
        
        # Test with Azure provider
        resources = parse_description(SAMPLE_DESCRIPTION, "azure")
        # Verify Azure-specific resources

# Test the generate_terraform_code function
def test_generate_terraform_code():
    # Convert to Resource objects
    from app import Resource
    resources = []
    for r in SAMPLE_RESOURCES:
        resources.append(Resource(
            type=r["type"],
            name=r["name"],
            parameters=r["parameters"]
        ))
    
    # Generate Terraform code
    tf_code = generate_terraform_code(resources, "aws")
    
    # Verify the generated code contains expected elements
    assert 'provider "aws"' in tf_code
    assert 'resource "aws_instance"' in tf_code
    assert 'resource "aws_security_group"' in tf_code
    assert 'resource "aws_s3_bucket"' in tf_code
    
    # Test with other cloud providers
    tf_code = generate_terraform_code([], "azure")
    assert 'provider "azurerm"' in tf_code
    
    tf_code = generate_terraform_code([], "gcp")
    assert 'provider "google"' in tf_code

# Test the estimate_cost function
def test_estimate_cost():
    # Convert to Resource objects
    from app import Resource
    resources = []
    for r in SAMPLE_RESOURCES:
        resources.append(Resource(
            type=r["type"],
            name=r["name"],
            parameters=r["parameters"]
        ))
    
    cost = estimate_cost(resources, "aws")
    assert isinstance(cost, float)
    assert cost > 0
    
    # Test with other cloud providers
    cost = estimate_cost([], "azure")
    assert cost == 0.0
    
    cost = estimate_cost([], "gcp")
    assert cost == 0.0

# Test the validate_terraform function
def test_validate_terraform():
    valid_tf = """
    resource "aws_instance" "example" {
      ami           = "ami-0c55b159cbfafe1f0"
      instance_type = "t2.micro"
    }
    """
    
    is_valid, message = validate_terraform(valid_tf)
    assert is_valid is True
    
    invalid_tf = """
    resource {
      bad syntax
    }
    """
    
    is_valid, message = validate_terraform(invalid_tf)
    assert is_valid is False

# API endpoint tests
def test_get_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_generate_endpoint():
    # Mock the necessary functions
    with patch('app.parse_description') as mock_parse, \
         patch('app.generate_terraform_code') as mock_generate, \
         patch('app.validate_terraform') as mock_validate, \
         patch('app.estimate_cost') as mock_estimate:
        
        # Setup mocks
        from app import Resource
        mock_resources = [Resource(type="aws_instance", name="test", parameters={})]
        mock_parse.return_value = mock_resources
        mock_generate.return_value = "terraform code here"
        mock_validate.return_value = (True, "Valid")
        mock_estimate.return_value = 42.0
        
        # Test the endpoint
        response = client.post(
            "/generate",
            json={
                "description": SAMPLE_DESCRIPTION,
                "cloud_provider": "aws",
                "include_cost_estimate": True
            }
        )
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Generated Terraform Code" in response.text
        assert "terraform code here" in response.text

# Test error handling
def test_generate_error_handling():
    # Mock parse_description to raise an exception
    with patch('app.parse_description') as mock_parse:
        mock_parse.side_effect = Exception("Test error")
        
        # Test the API endpoint
        response = client.post(
            "/generate",
            json={
                "description": SAMPLE_DESCRIPTION,
                "cloud_provider": "aws",
                "include_cost_estimate": True
            }
        )
        
        assert response.status_code == 500
        assert "detail" in response.json()
        
        # Test the HTML endpoint
        response = client.post(
            "/generate-html",
            data={
                "description": SAMPLE_DESCRIPTION,
                "cloud_provider": "aws",
                "include_cost_estimate": "true"
            }
        )
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Oops! Something went wrong" in response.text

# Integration test
@pytest.mark.integration
def test_full_integration():
    """
    This test is marked as an integration test and 
    requires a running application with all dependencies.
    """
    response = client.post(
        "/generate",
        json={
            "description": "Create a simple EC2 instance",
            "cloud_provider": "aws",
            "include_cost_estimate": True
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "terraform_code" in data
    assert "resources" in data
    assert isinstance(data["estimated_cost"], float) or data["estimated_cost"] is None

if __name__ == "__main__":
    pytest.main()

def test_generate_html_endpoint():
    # Mock the necessary functions
    with patch('app.parse_description') as mock_parse, \
         patch('app.generate_terraform_code') as mock_generate, \
         patch('app.validate_terraform') as mock_validate, \
         patch('app.estimate_cost') as mock_estimate:
        
        # Setup mocks
        from app import Resource
        mock_resources = [Resource(type="aws_instance", name="test", parameters={})]
        mock_parse.return_value = mock_resources
        mock_generate.return_value = "terraform code here"
        mock_validate.return_value = (True, "Valid")
        mock_estimate.return_value = 42.0
        
        # Test the endpoint
        response = client.post(
            "/generate-html",
            data={
                "description": SAMPLE_DESCRIPTION,
                "cloud_provider": "aws",
                "include_cost_estimate": "true"
            }
        )
        
        assert response.status_code == 200