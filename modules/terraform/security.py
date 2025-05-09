"""
Terraform Security Scanner

This module provides security scanning functionality for generated Terraform code.
It checks for common security misconfigurations and provides recommendations.
"""

import re
import json
from typing import Dict, List, Tuple, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Security rules based on best practices
SECURITY_RULES = [
    {
        "id": "SEC001",
        "name": "Public S3 Bucket",
        "description": "S3 buckets should not be publicly accessible",
        "severity": "HIGH",
        "pattern": r'resource\s+"aws_s3_bucket"\s+.+\s+acl\s+=\s+"public-read"',
        "recommendation": "Use private ACL and configure specific access through bucket policies"
    },
    {
        "id": "SEC002",
        "name": "Unrestricted Security Group Ingress",
        "description": "Security group allows unrestricted ingress from 0.0.0.0/0",
        "severity": "MEDIUM",
        "pattern": r'ingress\s+{.*?from_port\s+=\s+(\d+).*?to_port\s+=\s+\1.*?cidr_blocks\s+=\s+\[\s*"0\.0\.0\.0/0"\s*\]',
        "recommendation": "Restrict access to specific IP ranges or security groups"
    },
    {
        "id": "SEC003",
        "name": "Unencrypted EBS Volume",
        "description": "EBS volumes should be encrypted",
        "severity": "MEDIUM",
        "pattern": r'resource\s+"aws_ebs_volume".*?}',
        "negative_pattern": r'encrypted\s+=\s+true',
        "recommendation": "Add 'encrypted = true' to EBS volume configuration"
    },
    {
        "id": "SEC004",
        "name": "Unencrypted RDS Instance",
        "description": "RDS instances should be encrypted",
        "severity": "HIGH",
        "pattern": r'resource\s+"aws_db_instance".*?}',
        "negative_pattern": r'storage_encrypted\s+=\s+true',
        "recommendation": "Add 'storage_encrypted = true' to RDS instance configuration"
    },
    {
        "id": "SEC005",
        "name": "Plaintext Password",
        "description": "Passwords should not be stored in plaintext",
        "severity": "CRITICAL",
        "pattern": r'password\s+=\s+"[^$].*?"',
        "recommendation": "Use AWS Secrets Manager or Parameter Store to manage sensitive information"
    },
    {
        "id": "SEC006",
        "name": "Default VPC Usage",
        "description": "Using the default VPC is not recommended for production workloads",
        "severity": "LOW",
        "pattern": r'vpc_id\s+=\s+"vpc-\w+"',
        "recommendation": "Create a custom VPC with appropriate network segmentation"
    },
    {
        "id": "SEC007",
        "name": "Missing Resource Tags",
        "description": "Resources should have tags for better organization and security",
        "severity": "LOW",
        "pattern": r'resource\s+"aws_\w+".*?}',
        "negative_pattern": r'tags\s+=\s+{',
        "recommendation": "Add appropriate tags including Owner, Environment, and Purpose"
    },
    {
        "id": "SEC008",
        "name": "S3 Versioning Disabled",
        "description": "S3 buckets should have versioning enabled for data protection",
        "severity": "MEDIUM",
        "pattern": r'resource\s+"aws_s3_bucket".*?}',
        "negative_pattern": r'versioning\s+{.*?enabled\s+=\s+true',
        "recommendation": "Enable versioning to protect against accidental deletion and modifications"
    },
    {
        "id": "SEC009",
        "name": "Unprotected RDS Deletion",
        "description": "RDS instances should have deletion protection enabled",
        "severity": "MEDIUM",
        "pattern": r'resource\s+"aws_db_instance".*?}',
        "negative_pattern": r'deletion_protection\s+=\s+true',
        "recommendation": "Add 'deletion_protection = true' to prevent accidental deletion"
    },
    {
        "id": "SEC010",
        "name": "Weak TLS Configuration",
        "description": "TLS version should be 1.2 or higher",
        "severity": "HIGH",
        "pattern": r'min_protocol_version\s+=\s+"TLSv1(\.|_)(0|1)"',
        "recommendation": "Use at least TLSv1.2 for all TLS configurations"
    }
]

class SecurityIssue:
    def __init__(self, rule_id: str, rule_name: str, description: str, 
                 severity: str, recommendation: str, line: int, code_snippet: str):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.description = description
        self.severity = severity
        self.recommendation = recommendation
        self.line = line
        self.code_snippet = code_snippet
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "description": self.description,
            "severity": self.severity,
            "recommendation": self.recommendation,
            "line": self.line,
            "code_snippet": self.code_snippet
        }
    
    def __str__(self) -> str:
        return f"{self.rule_id} ({self.severity}): {self.rule_name} at line {self.line}"

def scan_terraform_code(tf_code: str) -> List[SecurityIssue]:
    """
    Scan Terraform code for security issues based on predefined rules.
    
    Args:
        tf_code: The Terraform code to scan
        
    Returns:
        List of SecurityIssue objects
    """
    issues = []
    lines = tf_code.split('\n')
    
    for rule in SECURITY_RULES:
        pattern = re.compile(rule["pattern"], re.DOTALL)
        matches = list(pattern.finditer(tf_code))
        
        for match in matches:
            # Check if there's a negative pattern to exclude false positives
            if "negative_pattern" in rule:
                neg_pattern = re.compile(rule["negative_pattern"])
                match_text = match.group(0)
                if neg_pattern.search(match_text):
                    continue  # Skip if negative pattern is found
            
            # Find the line number of the match
            match_start = match.start()
            line_no = tf_code[:match_start].count('\n') + 1
            
            # Extract the relevant code snippet
            start_line = max(0, line_no - 2)
            end_line = min(len(lines), line_no + 3)
            snippet = '\n'.join(lines[start_line:end_line])
            
            # Create the issue
            issue = SecurityIssue(
                rule_id=rule["id"],
                rule_name=rule["name"],
                description=rule["description"],
                severity=rule["severity"],
                recommendation=rule["recommendation"],
                line=line_no,
                code_snippet=snippet
            )
            issues.append(issue)
    
    return issues

def generate_security_report(tf_code: str) -> Dict[str, Any]:
    """
    Generate a comprehensive security report for Terraform code.
    
    Args:
        tf_code: The Terraform code to analyze
        
    Returns:
        Dictionary containing the security report
    """
    issues = scan_terraform_code(tf_code)
    
    # Count issues by severity
    severity_counts = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0
    }
    
    for issue in issues:
        if issue.severity in severity_counts:
            severity_counts[issue.severity] += 1
    
    # Calculate a security score (0-100)
    severity_weights = {
        "CRITICAL": 10,
        "HIGH": 5,
        "MEDIUM": 2,
        "LOW": 1
    }
    
    total_weight = sum(severity_weights.values())
    weighted_issues = sum(severity_counts[sev] * severity_weights[sev] for sev in severity_counts)
    
    max_score = 100
    if weighted_issues == 0:
        security_score = max_score
    else:
        # The more issues, the lower the score
        security_score = max(0, max_score - (weighted_issues * 5))
    
    # Generate report
    report = {
        "scan_summary": {
            "total_issues": len(issues),
            "severity_counts": severity_counts,
            "security_score": security_score,
            "security_grade": get_security_grade(security_score)
        },
        "issues": [issue.to_dict() for issue in issues],
        "recommendations": get_general_recommendations(issues)
    }
    
    return report

def get_security_grade(score: float) -> str:
    """
    Convert a security score to a letter grade.
    """
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"

def get_general_recommendations(issues: List[SecurityIssue]) -> List[str]:
    """
    Generate general security recommendations based on identified issues.
    """
    recommendations = []
    
    if any(issue.severity == "CRITICAL" for issue in issues):
        recommendations.append(
            "Critical security issues found. Fix these immediately before deploying to any environment."
        )
    
    categories = {
        "encryption": any(issue.rule_id in ["SEC003", "SEC004"] for issue in issues),
        "network": any(issue.rule_id in ["SEC002", "SEC006"] for issue in issues),
        "access": any(issue.rule_id in ["SEC001", "SEC005"] for issue in issues),
        "data_protection": any(issue.rule_id in ["SEC008", "SEC009"] for issue in issues)
    }
    
    if categories["encryption"]:
        recommendations.append(
            "Enhance encryption practices by enabling encryption for all storage resources and in-transit data."
        )
    
    if categories["network"]:
        recommendations.append(
            "Improve network security by implementing proper segmentation and restricting access to resources."
        )
    
    if categories["access"]:
        recommendations.append(
            "Strengthen access controls and consider implementing the principle of least privilege."
        )
    
    if categories["data_protection"]:
        recommendations.append(
            "Implement additional data protection mechanisms such as versioning, backups, and deletion protection."
        )
    
    # Add general best practices
    recommendations.append(
        "Consider implementing Infrastructure as Code (IaC) scanning in your CI/CD pipeline."
    )
    
    return recommendations

def fix_security_issues(tf_code: str, issues: List[SecurityIssue]) -> str:
    """
    Attempt to automatically fix some common security issues in Terraform code.
    
    Args:
        tf_code: The original Terraform code
        issues: List of identified security issues
        
    Returns:
        Modified Terraform code with some security issues fixed
    """
    modified_code = tf_code
    
    # Group issues by rule_id for batch processing
    issues_by_rule = {}
    for issue in issues:
        if issue.rule_id not in issues_by_rule:
            issues_by_rule[issue.rule_id] = []
        issues_by_rule[issue.rule_id].append(issue)
    
    # Apply fixes based on rule types
    if "SEC001" in issues_by_rule:  # Public S3 bucket
        modified_code = re.sub(
            r'(resource\s+"aws_s3_bucket"[^}]+)acl\s+=\s+"public-read"([^}]+)',
            r'\1acl = "private"\2',
            modified_code
        )
    
    if "SEC003" in issues_by_rule:  # Unencrypted EBS
        # Find EBS volumes without encryption and add encryption
        pattern = re.compile(r'(resource\s+"aws_ebs_volume"[^}]+?)(})', re.DOTALL)
        for match in pattern.finditer(modified_code):
            if "encrypted" not in match.group(1):
                replacement = f"{match.group(1)}  encrypted = true\n{match.group(2)}"
                modified_code = modified_code[:match.start()] + replacement + modified_code[match.end():]
    
    if "SEC004" in issues_by_rule:  # Unencrypted RDS
        # Find RDS instances without encryption and add encryption
        pattern = re.compile(r'(resource\s+"aws_db_instance"[^}]+?)(})', re.DOTALL)
        for match in pattern.finditer(modified_code):
            if "storage_encrypted" not in match.group(1):
                replacement = f"{match.group(1)}  storage_encrypted = true\n{match.group(2)}"
                modified_code = modified_code[:match.start()] + replacement + modified_code[match.end():]
    
    if "SEC005" in issues_by_rule:  # Plaintext passwords
        # Replace plaintext passwords with reference to AWS Secrets Manager
        modified_code = re.sub(
            r'password\s+=\s+"([^$].*?)"',
            r'password = aws_secretsmanager_secret_version.db_password.secret_string',
            modified_code
        )
        
        # Add the secrets manager resource if not already present
        if "aws_secretsmanager_secret" not in modified_code:
            secret_resource = """
resource "aws_secretsmanager_secret" "db_password" {
  name        = "db-password"
  description = "Database password"
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = "CHANGE_ME_BEFORE_DEPLOYMENT"
}
"""
            # Insert after the provider block
            provider_end = re.search(r'provider\s+".+?"\s+{[^}]*}', modified_code).end()
            modified_code = modified_code[:provider_end] + "\n" + secret_resource + modified_code[provider_end:]
    
    if "SEC007" in issues_by_rule:  # Missing tags
        # Find resources without tags and add basic tags
        pattern = re.compile(r'(resource\s+"aws_\w+"[^}]+?)(})', re.DOTALL)
        for match in pattern.finditer(modified_code):
            if "tags" not in match.group(1):
                replacement = f"{match.group(1)}  tags = {{\n    Environment = \"dev\"\n    ManagedBy = \"terraform\"\n  }}\n{match.group(2)}"
                modified_code = modified_code[:match.start()] + replacement + modified_code[match.end():]
    
    if "SEC008" in issues_by_rule:  # S3 versioning disabled
        # Find S3 buckets without versioning and add versioning
        pattern = re.compile(r'(resource\s+"aws_s3_bucket"[^}]+?)(})', re.DOTALL)
        for match in pattern.finditer(modified_code):
            if "versioning" not in match.group(1):
                replacement = f"{match.group(1)}  versioning {{\n    enabled = true\n  }}\n{match.group(2)}"
                modified_code = modified_code[:match.start()] + replacement + modified_code[match.end():]
    
    return modified_code

# Main functions to be used by the application
def check_terraform_security(tf_code: str) -> Dict[str, Any]:
    """
    Main entry point for checking Terraform code security.
    
    Args:
        tf_code: The Terraform code to check
        
    Returns:
        Dictionary containing the security report
    """
    logger.info("Scanning Terraform code for security issues")
    report = generate_security_report(tf_code)
    logger.info(f"Security scan completed. Found {len(report['issues'])} issues.")
    
    return report

def secure_terraform_code(tf_code: str) -> Tuple[str, Dict[str, Any]]:
    """
    Attempt to automatically secure Terraform code by fixing common issues.
    
    Args:
        tf_code: The original Terraform code
        
    Returns:
        Tuple containing the fixed code and a security report
    """
    logger.info("Attempting to automatically fix security issues in Terraform code")
    
    # First scan for issues
    issues = scan_terraform_code(tf_code)
    
    # Try to fix the issues
    fixed_code = fix_security_issues(tf_code, issues)
    
    # Scan again to see what issues remain
    updated_report = generate_security_report(fixed_code)
    
    logger.info(f"Fixed {len(issues) - len(updated_report['issues'])} out of {len(issues)} issues")
    
    return fixed_code, updated_report

if __name__ == "__main__":
    # Example usage
    sample_code = """
    provider "aws" {
      region = "us-west-2"
    }
    
    resource "aws_s3_bucket" "data" {
      bucket = "my-bucket"
      acl    = "public-read"
    }
    
    resource "aws_instance" "web" {
      ami           = "ami-0c55b159cbfafe1f0"
      instance_type = "t2.micro"
    }
    
    resource "aws_db_instance" "default" {
      allocated_storage    = 10
      engine               = "mysql"
      engine_version       = "5.7"
      instance_class       = "db.t3.micro"
      name                 = "mydb"
      username             = "admin"
      password             = "password123"
      skip_final_snapshot  = true
    }
    """
    
    report = check_terraform_security(sample_code)
    print(json.dumps(report, indent=2))
    
    fixed_code, updated_report = secure_terraform_code(sample_code)
    print("\nFixed Code:")
    print(fixed_code)
    print("\nUpdated Report:")
    print(json.dumps(updated_report, indent=2))