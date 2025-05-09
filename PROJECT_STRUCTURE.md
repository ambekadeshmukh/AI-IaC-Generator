# Project Structure Overview

This document outlines the organization of the IaC Generator project to help you understand how the components fit together.

```
iac-generator/
│
├── app.py                 # Main FastAPI application entry point
├── Dockerfile             # Docker configuration for containerization
├── docker-compose.yml     # Docker Compose configuration for local development
├── requirements.txt       # Python dependencies
├── setup.py               # Package installation configuration
├── .env                   # Environment variables (example provided as .env.example)
├── .gitignore             # Git ignore configurations
│
├── cloud_templates.py     # Templates for different cloud providers (AWS, Azure, GCP)
│
├── static/                # Static assets for the web interface
│   ├── css/               # Stylesheet files
│   ├── js/                # JavaScript files
│   └── images/            # Image assets
│
├── templates/             # Jinja2 HTML templates
│   ├── index.html         # Main landing page template
│   ├── result.html        # Results display template
│   ├── error.html         # Error page template
│   └── components/        # Reusable template components
│
├── modules/               # Core functionality modules
│   ├── nlp/               # Natural Language Processing components
│   │   ├── __init__.py
│   │   ├── entity_extractor.py  # Entity extraction from descriptions
│   │   └── training/      # NLP model training scripts and data
│   │
│   ├── terraform/         # Terraform code generation and validation
│   │   ├── __init__.py
│   │   ├── generator.py   # Core code generation logic
│   │   ├── validator.py   # Terraform validation utilities
│   │   └── security.py    # Security scanning for Terraform code
│   │
│   ├── cost/              # Cost estimation functionality
│   │   ├── __init__.py
│   │   ├── estimator.py   # Cost estimation logic
│   │   └── pricing_data/  # Cloud provider pricing data
│   │
│   └── api/               # API endpoints and route handlers
│       ├── __init__.py
│       ├── routes.py      # API route definitions
│       └── schemas.py     # Pydantic schemas for request/response
│
├── utils/                 # Utility functions and helpers
│   ├── __init__.py
│   ├── logging.py         # Logging configuration
│   ├── security.py        # Security utilities
│   └── visualization.py   # Infrastructure visualization helpers
│
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── test_app.py        # Main application tests
│   ├── test_nlp.py        # NLP component tests
│   ├── test_terraform.py  # Terraform generation tests
│   ├── test_security.py   # Security scanner tests
│   └── fixtures/          # Test fixtures and sample data
│
└── .github/               # GitHub configuration
    └── workflows/         # GitHub Actions CI/CD workflows
        └── main.yml       # Main CI/CD pipeline
```

## Key Components

### 1. Core Application (`app.py`)

The main FastAPI application that ties together all components. It handles HTTP requests, renders templates, and coordinates between different modules.

### 2. Cloud Templates (`cloud_templates.py`)

Contains Terraform templates for different cloud providers (AWS, Azure, GCP). These templates are used by the code generator.

### 3. NLP Module (`modules/nlp/`)

Responsible for parsing natural language descriptions and extracting infrastructure specifications. Uses spaCy and custom entity recognition.

### 4. Terraform Module (`modules/terraform/`)

Handles Terraform code generation, validation, and security scanning. This module contains the core logic for transforming infrastructure specifications into code.

### 5. Cost Estimation (`modules/cost/`)

Provides rough cost estimates for the generated infrastructure based on cloud provider pricing data.

### 6. Templates (`templates/`)

Contains Jinja2 HTML templates for the web interface. These templates are rendered by the FastAPI application.

### 7. Tests (`tests/`)

Comprehensive test suite for all components of the application. Includes unit tests, integration tests, and fixtures.

## Development Workflow

1. **Local Development:**
   ```bash
   # Run with hot-reloading
   docker-compose up --build
   ```

2. **Testing:**
   ```bash
   # Run tests
   pytest
   
   # Run specific tests
   pytest tests/test_nlp.py
   
   # Run with coverage report
   pytest --cov=./ --cov-report=term-missing
   ```

3. **Code Formatting:**
   ```bash
   # Format code
   black .
   
   # Sort imports
   isort .
   
   # Lint code
   flake8
   ```

4. **Building for Production:**
   ```bash
   # Build production Docker image
   docker build -t iac-generator:latest .
   
   # Run production container
   docker run -p 8000:8000 iac-generator:latest
   ```

## Deployment

The application is designed to be deployed as a Docker container. The provided GitHub Actions workflow (`/.github/workflows/main.yml`) automates the CI/CD process, building and deploying the application to your chosen environment.