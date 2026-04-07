"""Unit tests for cost_metrics.py (RC-143, RC-144, RC-145)."""

from unittest.mock import MagicMock, patch

import pytest

from app.rag.cost_metrics import (
    TokenUsage,
    emit_token_metrics,
    parse_usage_metadata,
)


# ---------------------------------------------------------------------------
# TokenUsage dataclass
# ---------------------------------------------------------------------------

class TestTokenUsage:
    def test_total_tokens(self):
        usage = TokenUsage(input_tokens=300, output_tokens=150)
        assert usage.total_tokens == 450

    def test_estimated_cost_usd(self):
        usage = TokenUsage(input_tokens=1000, output_tokens=1000)
        # 1k input * 0.001 + 1k output * 0.002 = 0.001 + 0.002 = 0.003
        cost = usage.estimated_cost_usd(
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
        )
        assert abs(cost - 0.003) < 1e-9

    def test_estimated_cost_zero_tokens(self):
        usage = TokenUsage(input_tokens=0, output_tokens=0)
        cost = usage.estimated_cost_usd(0.001, 0.002)
        assert cost == 0.0

    def test_estimated_cost_groq_pricing(self):
        """Validate with real Groq LLaMA 3.3-70B pricing."""
        usage = TokenUsage(input_tokens=500, output_tokens=200)
        cost = usage.estimated_cost_usd(
            cost_per_1k_input=0.00059,
            cost_per_1k_output=0.00079,
        )
        expected = (500 / 1000 * 0.00059) + (200 / 1000 * 0.00079)
        assert abs(cost - expected) < 1e-9


# ---------------------------------------------------------------------------
# parse_usage_metadata
# ---------------------------------------------------------------------------

class TestParseUsageMetadata:
    def test_full_metadata(self):
        um = {"input_tokens": 400, "output_tokens": 100, "total_tokens": 500}
        result = parse_usage_metadata(um)
        assert result is not None
        assert result.input_tokens == 400
        assert result.output_tokens == 100
        assert result.total_tokens == 500

    def test_missing_split_falls_back_to_total(self):
        """When only total_tokens is present, split 50/50."""
        um = {"total_tokens": 200}
        result = parse_usage_metadata(um)
        assert result is not None
        assert result.total_tokens == 200
        assert result.input_tokens + result.output_tokens == 200

    def test_none_input_returns_none(self):
        assert parse_usage_metadata(None) is None

    def test_empty_dict_returns_none(self):
        assert parse_usage_metadata({}) is None

    def test_all_zeros_returns_none(self):
        assert parse_usage_metadata({"input_tokens": 0, "output_tokens": 0}) is None

    def test_string_values_coerced(self):
        um = {"input_tokens": "300", "output_tokens": "150", "total_tokens": "450"}
        result = parse_usage_metadata(um)
        assert result is not None
        assert result.input_tokens == 300
        assert result.output_tokens == 150


# ---------------------------------------------------------------------------
# emit_token_metrics
# ---------------------------------------------------------------------------

class TestEmitTokenMetrics:
    def _make_usage(self):
        return TokenUsage(input_tokens=300, output_tokens=100)

    def test_emits_five_metrics(self):
        usage = self._make_usage()
        mock_client = MagicMock()

        with patch("boto3.client", return_value=mock_client):
            emit_token_metrics(
                role="finance",
                usage=usage,
                cost_per_1k_input=0.00059,
                cost_per_1k_output=0.00079,
                namespace="FinSolveAI/TokenUsage",
                aws_region="us-east-1",
            )

        mock_client.put_metric_data.assert_called_once()
        call_kwargs = mock_client.put_metric_data.call_args
        metric_data = call_kwargs.kwargs["MetricData"]

        names = {m["MetricName"] for m in metric_data}
        assert names == {
            "InputTokens",
            "OutputTokens",
            "TokensUsed",
            "EstimatedCostUSD",
            "RequestCount",
        }

    def test_role_dimension_set_correctly(self):
        usage = self._make_usage()
        mock_client = MagicMock()

        with patch("boto3.client", return_value=mock_client):
            emit_token_metrics(
                role="executive",
                usage=usage,
                cost_per_1k_input=0.00059,
                cost_per_1k_output=0.00079,
                namespace="FinSolveAI/TokenUsage",
                aws_region="us-east-1",
            )

        metric_data = mock_client.put_metric_data.call_args.kwargs["MetricData"]
        for metric in metric_data:
            assert metric["Dimensions"] == [{"Name": "Role", "Value": "executive"}]

    def test_correct_metric_values(self):
        usage = TokenUsage(input_tokens=400, output_tokens=200)
        mock_client = MagicMock()

        with patch("boto3.client", return_value=mock_client):
            emit_token_metrics(
                role="hr",
                usage=usage,
                cost_per_1k_input=0.001,
                cost_per_1k_output=0.002,
                namespace="FinSolveAI/TokenUsage",
                aws_region="us-east-1",
            )

        metric_data = mock_client.put_metric_data.call_args.kwargs["MetricData"]
        by_name = {m["MetricName"]: m["Value"] for m in metric_data}

        assert by_name["InputTokens"] == 400.0
        assert by_name["OutputTokens"] == 200.0
        assert by_name["TokensUsed"] == 600.0
        assert by_name["RequestCount"] == 1.0
        # (400/1000*0.001) + (200/1000*0.002) = 0.0004 + 0.0004 = 0.0008
        assert abs(by_name["EstimatedCostUSD"] - 0.0008) < 1e-9

    def test_boto3_failure_is_swallowed(self):
        """A boto3 error must never propagate — best-effort only."""
        usage = self._make_usage()

        with patch("boto3.client", side_effect=Exception("no credentials")):
            # Should not raise
            emit_token_metrics(
                role="marketing",
                usage=usage,
                cost_per_1k_input=0.00059,
                cost_per_1k_output=0.00079,
                namespace="FinSolveAI/TokenUsage",
                aws_region="us-east-1",
            )

    def test_namespace_passed_to_cloudwatch(self):
        usage = self._make_usage()
        mock_client = MagicMock()

        with patch("boto3.client", return_value=mock_client):
            emit_token_metrics(
                role="engineering",
                usage=usage,
                cost_per_1k_input=0.00059,
                cost_per_1k_output=0.00079,
                namespace="CustomNamespace/Test",
                aws_region="eu-west-1",
            )

        call_kwargs = mock_client.put_metric_data.call_args.kwargs
        assert call_kwargs["Namespace"] == "CustomNamespace/Test"
