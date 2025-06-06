#!/bin/bash
set -e

echo "Deleting ADOT Collector CloudFormation stack..."
aws cloudformation delete-stack --stack-name adot-collector

echo "Waiting for stack deletion to complete..."
aws cloudformation wait stack-delete-complete --stack-name adot-collector

if [ $? -eq 0 ]; then
  echo "ADOT Collector stack deleted successfully!"
else
  echo "Error: Failed to delete ADOT Collector stack. Please check the AWS CloudFormation console for details."
  exit 1
fi
