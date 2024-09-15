import re
from flask import Flask, render_template, request
from terraform_templates import TEMPLATES

app = Flask(__name__)

def parse_description(description):
    resources = []
    
    # EC2 Instance
    if re.search(r'EC2|instance', description, re.IGNORECASE):
        instance_type = re.search(r't2\.micro|t3\.nano|m5\.large', description, re.IGNORECASE)
        instance_type = instance_type.group() if instance_type else 't2.micro'
        resources.append(('ec2_instance', {
            'name': 'example_instance',
            'ami': 'ami-0c55b159cbfafe1f0',  # Amazon Linux 2 AMI
            'instance_type': instance_type
        }))
    
    # EBS Volume
    if re.search(r'EBS|volume', description, re.IGNORECASE):
        size = re.search(r'\d+\s*GB', description, re.IGNORECASE)
        size = int(size.group().replace('GB', '').strip()) if size else 1
        resources.append(('ebs_volume', {
            'name': 'example_volume',
            'az': 'us-west-2a',  # Example AZ
            'size': size
        }))
    
    # S3 Bucket
    if re.search(r'S3|bucket', description, re.IGNORECASE):
        bucket_name = re.search(r'named\s+(\w+)', description, re.IGNORECASE)
        bucket_name = bucket_name.group(1) if bucket_name else 'example-bucket'
        resources.append(('s3_bucket', {
            'name': bucket_name,
            'bucket_name': bucket_name,
            'acl': 'private'
        }))
    
    # VPC
    if re.search(r'VPC', description, re.IGNORECASE):
        cidr = re.search(r'\d+\.\d+\.\d+\.\d+/\d+', description)
        cidr = cidr.group() if cidr else '10.0.0.0/16'
        resources.append(('vpc', {
            'name': 'example_vpc',
            'cidr_block': cidr
        }))
    
    # Subnet
    if re.search(r'subnet', description, re.IGNORECASE):
        cidr = re.search(r'\d+\.\d+\.\d+\.\d+/\d+', description)
        cidr = cidr.group() if cidr else '10.0.1.0/24'
        resources.append(('subnet', {
            'name': 'example_subnet',
            'vpc_id': '${aws_vpc.example_vpc.id}',
            'cidr_block': cidr,
            'az': 'us-west-2a'  # Example AZ
        }))
    
    return resources

def generate_terraform_code(description):
    resources = parse_description(description)
    tf_code = ""
    
    for resource_type, params in resources:
        tf_code += TEMPLATES[resource_type].format(**params) + "\n"
    
    return tf_code if tf_code else "# Unable to generate Terraform code for the given description."

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        description = request.form['description']
        tf_code = generate_terraform_code(description)
        return render_template('result.html', tf_code=tf_code)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)