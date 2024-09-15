# AI-Powered Infrastructure as Code (IaC) Generator

This project uses natural language processing to generate Terraform code based on user descriptions of desired infrastructure.

## Features

- Generate Terraform code from natural language descriptions
- Support for common AWS resources (EC2, EBS, S3, VPC, Subnet)
- Web interface for easy interaction
- Basic optimization of generated Terraform code

## Prerequisites

- Python 3.8 or later
- Flask
- Terraform (for validation, optional)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/iac-generator.git
   cd iac-generator
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Start the Flask application:
   ```
   python iac_generator.py
   ```

2. Open a web browser and navigate to `http://localhost:5000`.

![Screenshot 2024-09-15 194306](https://github.com/user-attachments/assets/644ba9cd-ca3f-47af-80a4-a082c2c5d953)


3. Enter a description of your desired infrastructure and click "Generate Terraform Code".

![Screenshot 2024-09-15 194326](https://github.com/user-attachments/assets/5fb297f8-77a7-4db1-bf52-ae5f5f7db11b)


## Limitations

- The current implementation supports a limited set of AWS resources.
- The natural language processing is based on simple pattern matching and may not understand complex descriptions.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
