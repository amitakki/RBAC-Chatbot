terraform {
  required_version = ">= 1.7.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment to enable remote state (S3 backend):
  # backend "s3" {
  #   bucket = "finsolve-tfstate"
  #   key    = "staging/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "finsolve-chatbot"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
