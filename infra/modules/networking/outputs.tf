output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of the 2 public subnets (used by ALB)"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the 2 private subnets (used by ECS and Redis)"
  value       = aws_subnet.private[*].id
}

output "alb_sg_id" {
  description = "Security group ID for the Application Load Balancer"
  value       = aws_security_group.alb.id
}

output "ecs_sg_id" {
  description = "Security group ID for ECS tasks"
  value       = aws_security_group.ecs.id
}

output "redis_sg_id" {
  description = "Security group ID for the ElastiCache Redis cluster"
  value       = aws_security_group.redis.id
}

output "nat_gateway_id" {
  description = "ID of the NAT Gateway"
  value       = aws_nat_gateway.main.id
}
