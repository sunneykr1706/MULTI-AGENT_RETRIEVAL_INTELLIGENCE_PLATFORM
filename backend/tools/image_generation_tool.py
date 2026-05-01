"""Image generation tool — Replicate first, with Pollinations/HF fallbacks."""
from __future__ import annotations

import base64
import logging
import time
from urllib.parse import quote_plus
from uuid import uuid4

import requests

logger = logging.getLogger(__name__)


def _guess_mime(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    if image_bytes.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    return "image/png"


def _to_data_url(image_bytes: bytes) -> str:
    mime = _guess_mime(image_bytes)
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _generate_with_pollinations(prompt: str) -> tuple[bytes | None, str]:
    """Best-effort free fallback provider that doesn't require billing setup."""
    encoded = quote_plus(prompt)
    seed = uuid4().int % 1_000_000_000
    endpoints = [
        f"https://image.pollinations.ai/prompt/{encoded}?model=flux&width=1024&height=1024&seed={seed}",
        f"https://image.pollinations.ai/prompt/{encoded}?model=turbo&width=1024&height=1024&seed={seed}",
        f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}",
        f"https://image.pollinations.ai/prompt/{encoded}",
    ]
    last_error = "fallback provider returned no image bytes"
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=90)
            response.raise_for_status()
            content_type = (response.headers or {}).get("Content-Type", "").lower()
            if "image" not in content_type and not response.content:
                last_error = f"non-image response from {endpoint}"
                continue
            return response.content, ""
        except Exception as exc:
            last_error = f"{exc} ({endpoint})"
            continue
    return None, last_error


def _generate_with_huggingface(prompt: str, token: str, model: str) -> tuple[bytes | None, str]:
    if not token:
        return None, "HF_API_TOKEN is missing"
    endpoint = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"inputs": prompt}
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        content_type = (response.headers or {}).get("Content-Type", "").lower()
        if "image" in content_type and response.content:
            return response.content, ""
        return None, f"unexpected HF content-type: {content_type or 'unknown'}"
    except Exception as exc:
        return None, str(exc)


def _extract_first_url(output: object) -> str:
    if isinstance(output, str) and output.startswith("http"):
        return output
    if isinstance(output, list):
        for item in output:
            if isinstance(item, str) and item.startswith("http"):
                return item
            if isinstance(item, dict):
                for key in ("url", "image", "output", "file"):
                    value = item.get(key)
                    if isinstance(value, str) and value.startswith("http"):
                        return value
    if isinstance(output, dict):
        for key in ("url", "image", "output", "file"):
            value = output.get(key)
            if isinstance(value, str) and value.startswith("http"):
                return value
            if isinstance(value, list):
                for candidate in value:
                    if isinstance(candidate, str) and candidate.startswith("http"):
                        return candidate
    return ""


def _replicate_error(response: requests.Response) -> str:
    try:
        payload = response.json()
        detail = payload.get("detail") or payload.get("error") or payload
        return str(detail)
    except Exception:
        return response.text[:500] if response.text else f"HTTP {response.status_code}"


def _generate_with_replicate(prompt: str, token: str, model: str) -> tuple[bytes | None, str]:
    if not token:
        return None, "REPLICATE_API_TOKEN is missing"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "wait=60",
    }

    model_ref = (model or "black-forest-labs/flux-schnell").strip()
    if not model_ref:
        model_ref = "black-forest-labs/flux-schnell"

    if "/" in model_ref and ":" not in model_ref:
        endpoint = f"https://api.replicate.com/v1/models/{model_ref}/predictions"
        payload = {"input": {"prompt": prompt}}
        model_label = model_ref
    else:
        endpoint = "https://api.replicate.com/v1/predictions"
        payload = {"version": model_ref, "input": {"prompt": prompt}}
        model_label = model_ref

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
        if response.status_code >= 400:
            return None, f"create failed ({response.status_code}): {_replicate_error(response)}"
        prediction = response.json()
    except Exception as exc:
        return None, str(exc)

    status = str(prediction.get("status", "")).lower()
    get_url = ((prediction.get("urls") or {}).get("get") or "").strip()

    if status in {"starting", "processing"} and get_url:
        for _ in range(30):
            time.sleep(2)
            poll = requests.get(get_url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
            if poll.status_code >= 400:
                return None, f"poll failed ({poll.status_code}): {_replicate_error(poll)}"
            prediction = poll.json()
            status = str(prediction.get("status", "")).lower()
            if status in {"succeeded", "failed", "canceled"}:
                break

    if status != "succeeded":
        err = prediction.get("error") or f"prediction status: {status or 'unknown'}"
        return None, str(err)

    output_url = _extract_first_url(prediction.get("output"))
    if not output_url:
        return None, "prediction succeeded but no output URL found"

    try:
        download = requests.get(
            output_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=120,
        )
        download.raise_for_status()
        content_type = (download.headers or {}).get("Content-Type", "").lower()
        if "image" not in content_type and not download.content:
            return None, f"non-image output from replicate ({content_type or 'unknown'})"
        return download.content, model_label
    except Exception as exc:
        return None, str(exc)


def generate_image(
    prompt: str,
    replicate_api_token: str = "",
    replicate_image_model: str = "black-forest-labs/flux-schnell",
    hf_api_token: str = "",
    hf_image_model: str = "stabilityai/stable-diffusion-xl-base-1.0",
) -> str:
    """Generate an image from prompt using Replicate, then free fallback providers."""
    clean_prompt = (prompt or "").strip()
    if not clean_prompt:
        return "Image generation failed: prompt is empty."

    replicate_bytes, replicate_result = _generate_with_replicate(
        clean_prompt,
        replicate_api_token,
        replicate_image_model,
    )
    if replicate_bytes:
        return _to_data_url(replicate_bytes)

    pollinations_bytes, pollinations_error = _generate_with_pollinations(clean_prompt)
    if pollinations_bytes:
        return _to_data_url(pollinations_bytes)

    hf_bytes, hf_error = _generate_with_huggingface(clean_prompt, hf_api_token, hf_image_model)
    if hf_bytes:
        return _to_data_url(hf_bytes)

    return (
        "Image generation failed: all configured providers failed.\n"
        f"Replicate error: {replicate_result}\n"
        f"Pollinations error: {pollinations_error}\n"
        f"Hugging Face error: {hf_error}\n"
        "Tip: set REPLICATE_API_TOKEN in backend/.env as the primary provider."
    )
