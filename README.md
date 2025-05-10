# AI-Powered Infrastructure as Code (IaC) Generator

  
  ![Python](https://img.shields.io/badge/Python-3.11-blue)
  ![FastAPI](https://img.shields.io/badge/FastAPI-0.108.0-green)
  ![Terraform](https://img.shields.io/badge/Terraform-1.7.0-purple)
  
  <p>Generate Terraform code from natural language descriptions using AI-powered language understanding</p>
</div>

## 🌟 Features

- 🤖 **AI-Powered**: Uses advanced NLP to understand your infrastructure requirements
- ☁️ **Multi-Cloud Support**: Generate code for AWS, Azure, and Google Cloud
- 💰 **Cost Estimation**: Get approximate cost estimates for your infrastructure
- 📊 **Infrastructure Visualization**: Visual representation of your resources
- 🛡️ **Best Practices**: Follows infrastructure as code and security best practices
- 🚀 **REST API**: Use the generator programmatically via API endpoints
- 🔄 **Docker Support**: Easy deployment with Docker and docker-compose


## Architecture

![Ai-IaCgenerator](https://github.com/user-attachments/assets/e1e5a59f-10a8-4be9-9ee1-a94b320fc0b5)


## 📋 Prerequisites

- Python 3.11 or later
- Docker and docker-compose (optional)
- Terraform 1.0+ (for validation, optional)

## 🚀 Quick Start

### Using Docker (Recommended)

The easiest way to run the IaC Generator is using Docker and docker-compose:

```bash
# Clone the repository
git clone https://github.com/ambekadeshmukh/iac-generator.git
cd iac-generator

# Start the application with docker-compose
docker-compose up --build
```

Then visit `http://localhost:8000` in your browser.

### Manual Installation

If you prefer to run the application without Docker:

```bash
# Clone the repository
git clone https://github.com/ambekadeshmukh/iac-generator.git
cd iac-generator

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_lg

# Run the application
uvicorn app:app --reload
```

## 🔧 Configuration

The application can be configured through environment variables:

| Variable                | Description                                   | Default        |
|-------------------------|-----------------------------------------------|----------------|
| `DEBUG`                 | Enable debug mode                             | `False`        |
| `AWS_ACCESS_KEY_ID`     | AWS Access Key for cost estimation            | -              |
| `AWS_SECRET_ACCESS_KEY` | AWS Secret Key for cost estimation            | -              |
| `AWS_DEFAULT_REGION`    | Default AWS region                            | `us-west-2`    |
| `ENABLE_COST_ESTIMATION`| Enable or disable cost estimation             | `True`         |
| `PORT`                  | Port to run the application on                | `8000`         |

Create a `.env` file in the project root to set these variables:

```
DEBUG=True
AWS_DEFAULT_REGION=us-east-1
ENABLE_COST_ESTIMATION=True
```

## 📖 API Documentation

When the application is running, API documentation is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Example API Request

```bash
curl -X POST "http://localhost:8000/generate" \
     -H "Content-Type: application/json" \
     -d '{
           "description": "Create an EC2 instance with a security group and an S3 bucket",
           "cloud_provider": "aws",
           "include_cost_estimate": true
         }'
```

## 🧩 How It Works

1. **Natural Language Processing**: The application uses spaCy and custom entity recognition to parse your infrastructure description
2. **Resource Identification**: It identifies the resources you want to create and their configurations
3. **Terraform Generation**: Based on the identified resources, it generates the appropriate Terraform code
4. **Visualization**: It creates a visual representation of your infrastructure
5. **Cost Estimation**: It provides a rough estimate of the monthly cost (if enabled)

## 💻 Usage Examples

### Simple Web Server

```
Create an EC2 t2.micro instance with a security group allowing HTTP and SSH access, and a 20GB EBS volume
```

### Microservices Infrastructure

```
Set up an EKS cluster with 3 t3.medium worker nodes, an RDS Postgres database, and an ElastiCache Redis instance
```

### Static Website Hosting

```
Create an S3 bucket configured for static website hosting with CloudFront distribution for caching
```

## 🧪 Testing

Run the test suite with:

```bash
pytest
```

## Demo 

View the demo here - https://youtu.be/kuNb2WOlWHo

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please make sure to update tests as appropriate.

## 🔮 Future Improvements

- [ ] Add support for more cloud providers (DigitalOcean, Oracle Cloud, etc.)
- [ ] Improve cost estimation accuracy with real-time pricing APIs
- [ ] Add user accounts to save and manage generated infrastructures
- [ ] Enable export to other IaC formats (CloudFormation, Pulumi, etc.)
- [ ] Add integration with version control systems (GitHub, GitLab)
- [ ] Implement advanced security scanning of generated infrastructure
- [ ] Add support for infrastructure diagram exports (PNG, SVG, PDF)

## 🙏 Acknowledgements

- [Terraform](https://www.terraform.io/) - Infrastructure as Code tool
- [spaCy](https://spacy.io/) - Natural Language Processing library
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Tailwind CSS](https://tailwindcss.com/) - CSS framework
