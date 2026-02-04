"""
Token Usage and Cost Tracking for OpenAI API Calls

Tracks input/output tokens and calculates costs based on model pricing.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Any

from app.config import settings

logger = logging.getLogger("entitlements-chat.tokens")


# OpenAI pricing per 1M tokens (as of 2024)
# Prices in USD per 1M tokens
MODEL_PRICING = {
    # GPT-4o models
    "gpt-4o": {
        "input": 2.50,   # $2.50 per 1M input tokens
        "output": 10.00  # $10.00 per 1M output tokens
    },
    "gpt-4o-2024-08-06": {
        "input": 2.50,
        "output": 10.00
    },
    # GPT-4o-mini models
    "gpt-4o-mini": {
        "input": 0.15,   # $0.15 per 1M input tokens
        "output": 0.60  # $0.60 per 1M output tokens
    },
    "gpt-4o-mini-2024-07-18": {
        "input": 0.15,
        "output": 0.60
    },
    # GPT-4 Turbo models
    "gpt-4-turbo": {
        "input": 10.00,
        "output": 30.00
    },
    "gpt-4-turbo-preview": {
        "input": 10.00,
        "output": 30.00
    },
    "gpt-4-0125-preview": {
        "input": 10.00,
        "output": 30.00
    },
    # GPT-3.5 Turbo models
    "gpt-3.5-turbo": {
        "input": 0.50,
        "output": 1.50
    },
    "gpt-3.5-turbo-0125": {
        "input": 0.50,
        "output": 1.50
    },
}


@dataclass
class TokenUsage:
    """Token usage and cost information"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    model: str

    def to_dict(self) -> dict:
        """Convert to dictionary for logging"""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "input_cost_usd": round(self.input_cost_usd, 6),
            "output_cost_usd": round(self.output_cost_usd, 6),
            "total_cost_usd": round(self.total_cost_usd, 6),
            "model": self.model,
        }


def calculate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model: Optional[str] = None
) -> TokenUsage:
    """
    Calculate cost based on token usage and model pricing.
    
    Args:
        prompt_tokens: Number of input/prompt tokens
        completion_tokens: Number of output/completion tokens
        model: Model name (defaults to settings.openai_model)
    
    Returns:
        TokenUsage object with token counts and costs
    """
    if model is None:
        model = settings.openai_model
    
    # Get pricing for model (with fallback)
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        # Try to match by prefix (e.g., "gpt-4o-mini" matches "gpt-4o-mini-2024-07-18")
        for model_key, model_pricing in MODEL_PRICING.items():
            if model.startswith(model_key.split("-")[0]):  # Match prefix
                pricing = model_pricing
                break
        
        if not pricing:
            # Default to gpt-4o-mini pricing if unknown
            logger.warning(f"Unknown model pricing for {model}, using gpt-4o-mini pricing")
            pricing = MODEL_PRICING["gpt-4o-mini"]
    
    # Calculate costs (pricing is per 1M tokens)
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost
    
    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        total_cost_usd=total_cost,
        model=model,
    )


def extract_usage_from_response(usage: Optional[Any], model: Optional[str] = None) -> Optional[TokenUsage]:
    """
    Extract token usage from OpenAI API response.
    
    Args:
        usage: Usage object from OpenAI response (has prompt_tokens, completion_tokens attributes)
        model: Model name (defaults to settings.openai_model)
    
    Returns:
        TokenUsage object or None if usage is not available
    """
    if usage is None:
        return None
    
    # Extract token counts from usage object
    # Usage object has: prompt_tokens, completion_tokens, total_tokens
    try:
        prompt_tokens = getattr(usage, 'prompt_tokens', 0)
        completion_tokens = getattr(usage, 'completion_tokens', 0)
    except AttributeError:
        logger.warning("Usage object does not have expected attributes")
        return None
    
    return calculate_cost(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        model=model,
    )


def log_token_usage(usage: TokenUsage, context: str = ""):
    """
    Log token usage and cost information.
    
    Args:
        usage: TokenUsage object
        context: Additional context for the log message
    """
    context_str = f" [{context}]" if context else ""
    logger.info(
        f"Token usage{context_str}: "
        f"prompt={usage.prompt_tokens}, "
        f"completion={usage.completion_tokens}, "
        f"total={usage.total_tokens}, "
        f"cost=${usage.total_cost_usd:.6f} "
        f"(input=${usage.input_cost_usd:.6f}, output=${usage.output_cost_usd:.6f}) "
        f"model={usage.model}"
    )


def log_token_usage_dict(usage_dict: dict, context: str = ""):
    """
    Log token usage from dictionary format.
    
    Args:
        usage_dict: Dictionary with token usage information
        context: Additional context for the log message
    """
    if not usage_dict:
        return
    
    context_str = f" [{context}]" if context else ""
    logger.info(
        f"Token usage{context_str}: "
        f"prompt={usage_dict.get('prompt_tokens', 0)}, "
        f"completion={usage_dict.get('completion_tokens', 0)}, "
        f"total={usage_dict.get('total_tokens', 0)}, "
        f"cost=${usage_dict.get('total_cost_usd', 0):.6f} "
        f"(input=${usage_dict.get('input_cost_usd', 0):.6f}, "
        f"output=${usage_dict.get('output_cost_usd', 0):.6f}) "
        f"model={usage_dict.get('model', 'unknown')}"
    )

