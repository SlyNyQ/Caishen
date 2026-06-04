from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any, Protocol
import uuid

from app.config import SUPPORTED_PROVIDERS, Settings
from app.errors import ModelInvocationError, ResourceNotReadyError, ValidationError


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    route: str
    user_message: str
    system_prompt: str
    prompt: str
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class GenerationResult:
    text: str
    provider: str
    model: str
    request_id: str
    usage: dict[str, int] = field(default_factory=dict)


class GenerationClient(Protocol):
    def generate(
        self,
        request: GenerationRequest,
        *,
        provider: str,
        model: str | None,
    ) -> GenerationResult:
        ...


def _first_available_snapshot(tool_results: list[dict[str, Any]]) -> dict[str, Any] | None:
    for trace in tool_results:
        if trace.get("name") != "market_snapshot":
            continue
        result = trace.get("result")
        if isinstance(result, dict) and result.get("status") == "available":
            return result
    return None


class ProviderRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def resolve(self, provider: str | None, model: str | None) -> tuple[str, str]:
        selected_provider = (provider or self.settings.default_provider).strip().lower()
        if selected_provider not in SUPPORTED_PROVIDERS:
            raise ValidationError(f"Unsupported provider: {selected_provider}.")
        configured_model = self.settings.model_for(selected_provider)
        if model and model != configured_model:
            raise ValidationError(
                f"Model '{model}' is not allowlisted for {selected_provider}. "
                f"Use '{configured_model}'."
            )
        if selected_provider not in self.settings.configured_providers():
            raise ResourceNotReadyError(
                f"The {selected_provider} provider is not configured on the server."
            )
        return selected_provider, configured_model

    def generate(
        self,
        request: GenerationRequest,
        *,
        provider: str | None,
        model: str | None,
    ) -> GenerationResult:
        selected_provider, selected_model = self.resolve(provider, model)
        if selected_provider == "mock":
            return self._generate_mock(request, selected_model)
        if selected_provider == "openai":
            return self._generate_openai(request, selected_model)
        if selected_provider == "anthropic":
            return self._generate_anthropic(request, selected_model)
        if selected_provider == "google":
            return self._generate_google(request, selected_model)
        return self._generate_bedrock(request, selected_model)

    def _generate_mock(self, request: GenerationRequest, model: str) -> GenerationResult:
        snapshot = _first_available_snapshot(request.tool_results)
        if snapshot:
            change = snapshot.get("percent_change")
            change_text = "with an unavailable daily change"
            if isinstance(change, (int, float)):
                direction = "up" if change >= 0 else "down"
                change_text = f"{direction} {abs(change):.2f}% from the previous close"
            text = (
                f"{snapshot.get('ticker')} is currently {change_text}. "
                "Use the market snapshot, risk notes, and source context as research inputs rather than a trade instruction."
            )
        elif request.citations:
            text = (
                "The available Caishen research notes explain the concept below. "
                "Review the cited material and verify any time-sensitive market facts independently."
            )
        elif request.route == "source_analysis":
            text = "The supplied source was reviewed. Use its summary as context, and verify claims against primary market disclosures."
        else:
            text = (
                "Caishen can explain market concepts, compare securities, and outline educational scenarios. "
                "Add one or more tickers or a public source URL for a grounded analysis."
            )
        return GenerationResult(
            text=text,
            provider="mock",
            model=model,
            request_id=f"mock-{uuid.uuid4().hex[:12]}",
            usage={
                "input_tokens": max(1, len(request.prompt.split())),
                "output_tokens": max(1, len(text.split())),
            },
        )

    def _generate_openai(self, request: GenerationRequest, model: str) -> GenerationResult:
        try:
            from openai import OpenAI

            response = OpenAI(api_key=os.getenv("OPENAI_API_KEY")).chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.prompt},
                ],
            )
            text = response.choices[0].message.content or ""
            usage = response.usage
            return GenerationResult(
                text=text,
                provider="openai",
                model=model,
                request_id=response.id,
                usage={
                    "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                    "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
                },
            )
        except Exception as exc:
            raise ModelInvocationError("OpenAI generation failed.", detail=str(exc)) from exc

    def _generate_anthropic(self, request: GenerationRequest, model: str) -> GenerationResult:
        try:
            from anthropic import Anthropic

            response = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")).messages.create(
                model=model,
                max_tokens=1200,
                system=request.system_prompt,
                messages=[{"role": "user", "content": request.prompt}],
            )
            text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
            return GenerationResult(
                text=text,
                provider="anthropic",
                model=model,
                request_id=response.id,
                usage={
                    "input_tokens": int(response.usage.input_tokens),
                    "output_tokens": int(response.usage.output_tokens),
                },
            )
        except Exception as exc:
            raise ModelInvocationError("Anthropic generation failed.", detail=str(exc)) from exc

    def _generate_google(self, request: GenerationRequest, model: str) -> GenerationResult:
        try:
            import google.generativeai as genai

            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            response = genai.GenerativeModel(
                model,
                system_instruction=request.system_prompt,
            ).generate_content(request.prompt)
            return GenerationResult(
                text=response.text,
                provider="google",
                model=model,
                request_id=f"google-{uuid.uuid4().hex[:12]}",
            )
        except Exception as exc:
            raise ModelInvocationError("Google generation failed.", detail=str(exc)) from exc

    def _generate_bedrock(self, request: GenerationRequest, model: str) -> GenerationResult:
        try:
            import boto3

            response = boto3.client("bedrock-runtime", region_name=self.settings.aws_region).converse(
                modelId=model,
                system=[{"text": request.system_prompt}],
                messages=[{"role": "user", "content": [{"text": request.prompt}]}],
            )
            blocks = response.get("output", {}).get("message", {}).get("content", [])
            text = " ".join(block.get("text", "") for block in blocks if isinstance(block, dict)).strip()
            usage = response.get("usage", {})
            return GenerationResult(
                text=text,
                provider="bedrock",
                model=model,
                request_id=response.get("ResponseMetadata", {}).get("RequestId", f"bedrock-{uuid.uuid4().hex[:12]}"),
                usage={
                    "input_tokens": int(usage.get("inputTokens", 0)),
                    "output_tokens": int(usage.get("outputTokens", 0)),
                },
            )
        except Exception as exc:
            raise ModelInvocationError("Bedrock generation failed.", detail=str(exc)) from exc
