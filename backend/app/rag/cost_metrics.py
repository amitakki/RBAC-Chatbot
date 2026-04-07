"""
CloudWatch custom metric emission for token usage and cost tracking (RC-143, RC-144).

Emits per-request metrics to the ``FinSolveAI/TokenUsage`` namespace with a
``Role`` dimension so that CloudWatch can aggregate daily cost totals per role
(RC-145).

All emission is best-effort: any boto3 / credentials failure is swallowed and
logged at WARNING level so the user request is never impacted.

Metrics emitted per call to :func:`emit_token_metrics`:
  - ``InputTokens``      — prompt token count
  - ``OutputTokens``     — completion token count
  - ``TokensUsed``       — total tokens (input + output)
  - ``EstimatedCostUSD`` — computed from per-token pricing env vars
  - ``RequestCount``     — always 1; used by the HighHourlyQueries alarm
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Token counts extracted from a Groq ``usage_metadata`` dict."""

    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def estimated_cost_usd(
        self,
        cost_per_1k_input: float,
        cost_per_1k_output: float,
    ) -> float:
        """Return estimated cost in USD for this usage."""
        return (
            self.input_tokens / 1000 * cost_per_1k_input
            + self.output_tokens / 1000 * cost_per_1k_output
        )


def parse_usage_metadata(usage_metadata: dict | None) -> TokenUsage | None:
    """Extract :class:`TokenUsage` from a LangChain ``usage_metadata`` dict.

    Returns ``None`` if the dict is absent or lacks the expected keys.
    LangChain-Groq populates ``input_tokens``, ``output_tokens``, and
    ``total_tokens`` inside ``AIMessage.usage_metadata``.
    """
    if not usage_metadata:
        return None
    try:
        input_tokens = int(usage_metadata.get("input_tokens", 0))
        output_tokens = int(usage_metadata.get("output_tokens", 0))
        if input_tokens == 0 and output_tokens == 0:
            # Fall back to total only — split evenly as an estimate
            total = int(usage_metadata.get("total_tokens", 0))
            if total == 0:
                return None
            input_tokens = total // 2
            output_tokens = total - input_tokens
        return TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)
    except (TypeError, ValueError):
        return None


def emit_token_metrics(
    role: str,
    usage: TokenUsage,
    cost_per_1k_input: float,
    cost_per_1k_output: float,
    namespace: str,
    aws_region: str,
) -> None:
    """Put four custom metrics to CloudWatch for one completed RAG request.

    Args:
        role: The authenticated user's role (e.g. ``"finance"``). Used as the
            ``Role`` dimension value on every metric.
        usage: Token counts for this request.
        cost_per_1k_input: USD cost per 1 000 input tokens.
        cost_per_1k_output: USD cost per 1 000 output tokens.
        namespace: CloudWatch custom metric namespace.
        aws_region: AWS region where metrics are emitted.
    """
    try:
        import boto3  # noqa: PLC0415 — optional heavy import

        estimated_cost = usage.estimated_cost_usd(cost_per_1k_input, cost_per_1k_output)
        dimensions = [{"Name": "Role", "Value": role}]

        metric_data = [
            {
                "MetricName": "InputTokens",
                "Dimensions": dimensions,
                "Value": float(usage.input_tokens),
                "Unit": "Count",
            },
            {
                "MetricName": "OutputTokens",
                "Dimensions": dimensions,
                "Value": float(usage.output_tokens),
                "Unit": "Count",
            },
            {
                "MetricName": "TokensUsed",
                "Dimensions": dimensions,
                "Value": float(usage.total_tokens),
                "Unit": "Count",
            },
            {
                "MetricName": "EstimatedCostUSD",
                "Dimensions": dimensions,
                "Value": estimated_cost,
                "Unit": "None",
            },
            {
                "MetricName": "RequestCount",
                "Dimensions": dimensions,
                "Value": 1.0,
                "Unit": "Count",
            },
        ]

        client = boto3.client("cloudwatch", region_name=aws_region)
        client.put_metric_data(Namespace=namespace, MetricData=metric_data)

        logger.debug(
            "CloudWatch metrics emitted: role=%s tokens=%d cost=%.6f USD",
            role,
            usage.total_tokens,
            estimated_cost,
        )
    except Exception:
        logger.warning(
            "Failed to emit CloudWatch metrics for role=%s — metrics skipped",
            role,
            exc_info=True,
        )
