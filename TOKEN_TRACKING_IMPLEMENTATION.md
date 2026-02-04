# Token Usage and Cost Tracking Implementation

## Overview

This document describes the implementation of token usage tracking and cost metrics logging for all OpenAI API calls in the chat application.

## Features

1. **Token Counting**: Tracks input (prompt) tokens, output (completion) tokens, and total tokens
2. **Cost Calculation**: Automatically calculates costs based on model pricing
3. **Structured Logging**: Logs token usage and costs with context for each API call
4. **Model Support**: Supports multiple OpenAI models with their respective pricing

## Implementation

### 1. Token Tracker Module

**File**: `backend/app/token_tracker.py`

This module provides:
- `TokenUsage` dataclass: Stores token counts and costs
- `calculate_cost()`: Calculates costs based on token usage and model
- `extract_usage_from_response()`: Extracts usage from OpenAI API response
- `log_token_usage()`: Logs token usage and costs

### 2. Model Pricing

The module includes pricing for common OpenAI models (as of 2024):

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4-turbo | $10.00 | $30.00 |
| gpt-3.5-turbo | $0.50 | $1.50 |

**Note**: Pricing is configurable in `MODEL_PRICING` dictionary. Update as needed when OpenAI changes pricing.

### 3. Integration Points

Token tracking has been added to all OpenAI API calls:

1. **`llm_openai.py`** - `answer_with_context()`
   - Context: `answer_with_context`
   - Tracks tokens for RAG-based answers

2. **`sql_generate_v2.py`** - `_generate_sql()`
   - Context: `sql_generation`
   - Tracks tokens for SQL generation

3. **`sql_generate_v2.py`** - `_self_correct()`
   - Context: `sql_self_correction`
   - Tracks tokens for SQL self-correction

4. **`intent_router.py`** - `classify_intent()`
   - Context: `intent_classification`
   - Tracks tokens for intent classification

5. **`sql_generate.py`** - `generate_sql_plan()`
   - Context: `legacy_sql_generation`
   - Tracks tokens for legacy SQL generation

## Log Format

Token usage is logged in the following format:

```
INFO:entitlements-chat.tokens: Token usage [context]: prompt=1234, completion=567, total=1801, cost=$0.001234 (input=$0.000185, output=$0.000340) model=gpt-4o-mini
```

**Fields:**
- `prompt`: Input/prompt tokens
- `completion`: Output/completion tokens
- `total`: Total tokens
- `cost`: Total cost in USD
- `input`: Input cost in USD
- `output`: Output cost in USD
- `model`: Model name used

## Example Log Output

```
INFO:entitlements-chat.intent_router: classify_intent raw LLM content: {"intent": "generic_sql"}
INFO:entitlements-chat.tokens: Token usage [intent_classification]: prompt=245, completion=12, total=257, cost=$0.000039 (input=$0.000037, output=$0.000007) model=gpt-4o-mini

INFO:entitlements-chat.schema_retrieval: Schema retrieval: Retrieved schema context length: 5234 chars
INFO:entitlements-chat.sql_generate_v2: Enhanced SQL generation raw LLM content: {"mode":"sql","sql":"SELECT ...","reasoning":"..."}
INFO:entitlements-chat.tokens: Token usage [sql_generation]: prompt=5234, completion=234, total=5468, cost=$0.000820 (input=$0.000785, output=$0.000140) model=gpt-4o-mini
```

## Usage

### Automatic Tracking

Token tracking is automatic for all OpenAI API calls. No additional code is needed.

### Manual Tracking (if needed)

If you need to track tokens manually:

```python
from app.token_tracker import calculate_cost, log_token_usage

# Calculate cost from token counts
usage = calculate_cost(
    prompt_tokens=1000,
    completion_tokens=500,
    model="gpt-4o-mini"
)

# Log usage
log_token_usage(usage, context="my_custom_context")
```

### Extracting Usage from Response

```python
from app.token_tracker import extract_usage_from_response

resp = client.chat.completions.create(...)
usage = extract_usage_from_response(resp.usage, model=settings.openai_model)
if usage:
    log_token_usage(usage, context="my_context")
```

## Cost Calculation

Costs are calculated as:

```
input_cost = (prompt_tokens / 1,000,000) * input_price_per_1M
output_cost = (completion_tokens / 1,000,000) * output_price_per_1M
total_cost = input_cost + output_cost
```

## Benefits

1. **Cost Visibility**: See exactly how much each API call costs
2. **Usage Monitoring**: Track token usage patterns
3. **Budget Management**: Monitor costs to stay within budget
4. **Optimization**: Identify expensive operations for optimization
5. **Audit Trail**: Complete record of all API usage

## Updating Pricing

To update model pricing, edit `MODEL_PRICING` in `token_tracker.py`:

```python
MODEL_PRICING = {
    "gpt-4o-mini": {
        "input": 0.15,   # Update these values
        "output": 0.60
    },
    # Add new models here
}
```

## Log Aggregation

For production, consider:
1. **Structured Logging**: Export logs to a logging service (e.g., Datadog, CloudWatch)
2. **Metrics Collection**: Aggregate token usage and costs
3. **Alerting**: Set up alerts for high costs or usage spikes
4. **Dashboard**: Create dashboards for cost monitoring

## Files Modified

1. `backend/app/token_tracker.py` (NEW) - Token tracking utility
2. `backend/app/llm_openai.py` - Added token tracking
3. `backend/app/sql_generate_v2.py` - Added token tracking (2 locations)
4. `backend/app/intent_router.py` - Added token tracking
5. `backend/app/sql_generate.py` - Added token tracking

## Testing

To verify token tracking is working:

1. **Check Logs**: Look for `Token usage` log messages after each API call
2. **Verify Costs**: Ensure costs match expected values for your model
3. **Test Different Models**: Switch models and verify pricing updates

## Future Enhancements

Potential improvements:
1. **Database Storage**: Store token usage in database for analytics
2. **User-Level Tracking**: Track costs per user/conversation
3. **Rate Limiting**: Implement rate limiting based on costs
4. **Budget Alerts**: Alert when approaching budget limits
5. **Cost Reports**: Generate daily/weekly cost reports

