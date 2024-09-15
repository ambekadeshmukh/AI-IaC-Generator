import unittest
from unittest.mock import patch
from iac_generator import generate_terraform_code, optimize_terraform_code, validate_terraform_code

class TestIaCGenerator(unittest.TestCase):
    @patch('boto3.client')
    def test_generate_terraform_code(self, mock_client):
        mock_client.return_value.generate_code.return_value = {
            'Candidates': [{'Content': 'resource "aws_instance" "example" {}'}]
        }
        result = generate_terraform_code("Create an EC2 instance")
        self.assertEqual(result, 'resource "aws_instance" "example" {}')

    def test_optimize_terraform_code(self):
        input_code = 'resource "aws_instance" "example" {}'
        expected_output = 'resource "aws_instance" "example" {\n  tags = {\n    generated_by = "iac-generator"\n  }\n}'
        result = optimize_terraform_code(input_code)
        self.assertEqual(result.strip(), expected_output.strip())

    @patch('subprocess.run')
    def test_validate_terraform_code(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Success! The configuration is valid."
        is_valid, message = validate_terraform_code()
        self.assertTrue(is_valid)
        self.assertEqual(message, "Success! The configuration is valid.")

if __name__ == '__main__':
    unittest.main()