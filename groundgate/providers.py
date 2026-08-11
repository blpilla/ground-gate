"""Provider-agnostic LLM judges: OpenAI, Anthropic, Bedrock and Ollama.

Every provider is an optional extra; importing this module never imports a
provider SDK until the corresponding judge is instantiated. Ollama uses the
standard library only, keeping the fully local path dependency-free.
"""

from __future__ import annotations

import json
import urllib.request

from .judge import JudgeResult, build_prompt, parse_judge_response

_MAX_TOKENS = 300


class OpenAIJudge:
    """Judge backed by the OpenAI API (or any OpenAI-compatible endpoint)."""

    def __init__(self, model: str = "gpt-4o-mini", client=None, **client_kwargs):
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover
                raise ImportError(
                    "OpenAIJudge requires the 'openai' extra: pip install groundgate[openai]"
                ) from exc
            client = OpenAI(**client_kwargs)
        self._client = client
        self.model = model

    def judge(self, claim: str, evidence: str) -> JudgeResult:
        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=_MAX_TOKENS,
            temperature=0,
            messages=[{"role": "user", "content": build_prompt(claim, evidence)}],
        )
        return parse_judge_response(response.choices[0].message.content)


class AnthropicJudge:
    """Judge backed by the Anthropic API."""

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        client=None,
        **client_kwargs,
    ):
        if client is None:
            try:
                from anthropic import Anthropic
            except ImportError as exc:  # pragma: no cover
                raise ImportError(
                    "AnthropicJudge requires the 'anthropic' extra: "
                    "pip install groundgate[anthropic]"
                ) from exc
            client = Anthropic(**client_kwargs)
        self._client = client
        self.model = model

    def judge(self, claim: str, evidence: str) -> JudgeResult:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=_MAX_TOKENS,
            messages=[{"role": "user", "content": build_prompt(claim, evidence)}],
        )
        return parse_judge_response(response.content[0].text)


class BedrockJudge:
    """Judge backed by AWS Bedrock via the Converse API."""

    def __init__(
        self,
        model: str = "anthropic.claude-haiku-4-5-20251001-v1:0",
        client=None,
        **client_kwargs,
    ):
        if client is None:
            try:
                import boto3
            except ImportError as exc:  # pragma: no cover
                raise ImportError(
                    "BedrockJudge requires the 'bedrock' extra: pip install groundgate[bedrock]"
                ) from exc
            client = boto3.client("bedrock-runtime", **client_kwargs)
        self._client = client
        self.model = model

    def judge(self, claim: str, evidence: str) -> JudgeResult:
        response = self._client.converse(
            modelId=self.model,
            messages=[
                {"role": "user", "content": [{"text": build_prompt(claim, evidence)}]}
            ],
            inferenceConfig={"maxTokens": _MAX_TOKENS, "temperature": 0},
        )
        text = response["output"]["message"]["content"][0]["text"]
        return parse_judge_response(text)


class OllamaJudge:
    """Judge backed by a local Ollama server. Standard library only."""

    def __init__(
        self,
        model: str = "llama3.1",
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def judge(self, claim: str, evidence: str) -> JudgeResult:
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": build_prompt(claim, evidence),
                "stream": False,
                "options": {"temperature": 0},
            }
        ).encode()
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            body = json.loads(response.read().decode())
        return parse_judge_response(body.get("response", ""))
