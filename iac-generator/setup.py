from setuptools import setup, find_packages

setup(
    name='iac-generator',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'boto3',
        'terraform-parser',
        'click',
        'Flask',
    ],
    entry_points={
        'console_scripts': [
            'iac-generator=iac_generator:cli',
        ],
    },
)