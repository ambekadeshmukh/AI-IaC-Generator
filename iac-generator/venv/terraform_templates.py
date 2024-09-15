TEMPLATES = {
    "ec2_instance": """
resource "aws_instance" "{name}" {{
  ami           = "{ami}"
  instance_type = "{instance_type}"
  tags = {{
    Name = "{name}"
  }}
}}
""",
    "ebs_volume": """
resource "aws_ebs_volume" "{name}" {{
  availability_zone = "{az}"
  size              = {size}
  tags = {{
    Name = "{name}"
  }}
}}
""",
    "s3_bucket": """
resource "aws_s3_bucket" "{name}" {{
  bucket = "{bucket_name}"
  acl    = "{acl}"
  tags = {{
    Name = "{name}"
  }}
}}
""",
    "vpc": """
resource "aws_vpc" "{name}" {{
  cidr_block = "{cidr_block}"
  tags = {{
    Name = "{name}"
  }}
}}
""",
    "subnet": """
resource "aws_subnet" "{name}" {{
  vpc_id     = {vpc_id}
  cidr_block = "{cidr_block}"
  availability_zone = "{az}"
  tags = {{
    Name = "{name}"
  }}
}}
"""
}