"""
OpenAI API wrapper that automatically tracks gas meter costs.

Supports both:
1. Direct OpenAI client calls (client.chat.completions.create)
2. LangChain ChatOpenAI calls (llm.invoke)

Usage:
    from gas_meter.openai_wrapper import track_openai_call, track_langchain_call
    
    # Direct OpenAI client
    response = track_openai_call(
        client.chat.completions.create,
        model="gpt-4o-mini",
        messages=[...],
        max_tokens=500
    )
    
    # LangChain ChatOpenAI
    response = track_langchain_call(llm, model="gpt-4o-mini", prompt="...")
"""

from typing import Callable, Any, Optional
from gas_meter.tracker import get_gas_meter_tracker


def track_openai_call(
    openai_func: Callable,
    model: str,
    *args,
    **kwargs
) -> Any:
    """
    Wrapper for OpenAI API calls that automatically tracks token usage and costs.
    
    Args:
        openai_func: OpenAI API function (e.g., client.chat.completions.create)
        model: Model name (e.g., "gpt-4o-mini")
        *args, **kwargs: Arguments to pass to the OpenAI function
    
    Returns:
        Response from OpenAI API
    
    Example:
        response = track_openai_call(
            client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=500
        )
    """
    tracker = get_gas_meter_tracker()
    
    # Make the OpenAI API call
    response = openai_func(*args, **kwargs)
    
    # Extract token usage from response
    try:
        if hasattr(response, 'usage'):
            usage = response.usage
            if usage:
                input_tokens = getattr(usage, 'prompt_tokens', 0) or 0
                output_tokens = getattr(usage, 'completion_tokens', 0) or 0
                
                # Track the usage
                tracker.track_llm_usage(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
        elif hasattr(response, 'choices') and len(response.choices) > 0:
            # Try to get usage from response object directly
            if hasattr(response, 'usage'):
                usage = response.usage
                input_tokens = getattr(usage, 'prompt_tokens', 0) or 0
                output_tokens = getattr(usage, 'completion_tokens', 0) or 0
                tracker.track_llm_usage(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
    except Exception as e:
        # Don't fail the API call if tracking fails
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to track gas meter usage: {e}")
    
    return response


def track_langchain_call(
    llm: Any,
    model: str,
    prompt: str,
    *args,
    **kwargs
) -> Any:
    """
    Wrapper for LangChain ChatOpenAI calls that automatically tracks token usage.
    
    Args:
        llm: LangChain ChatOpenAI instance
        model: Model name (e.g., "gpt-4o-mini")
        prompt: The prompt to send
        *args, **kwargs: Additional arguments for llm.invoke
    
    Returns:
        Response from LangChain
    
    Example:
        response = track_langchain_call(llm, model="gpt-4o-mini", prompt="Hello")
    """
    tracker = get_gas_meter_tracker()
    
    # Make the LangChain call
    response = llm.invoke(prompt, *args, **kwargs)
    
    # Extract token usage from LangChain response
    try:
        # LangChain responses have response_metadata with token usage
        if hasattr(response, 'response_metadata'):
            metadata = response.response_metadata
            if metadata and 'token_usage' in metadata:
                token_usage = metadata['token_usage']
                input_tokens = token_usage.get('prompt_tokens', 0) or 0
                output_tokens = token_usage.get('completion_tokens', 0) or 0
                
                tracker.track_llm_usage(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
        # Alternative: check for usage_metadata attribute
        elif hasattr(response, 'usage_metadata'):
            usage_meta = response.usage_metadata
            input_tokens = getattr(usage_meta, 'input_tokens', 0) or 0
            output_tokens = getattr(usage_meta, 'output_tokens', 0) or 0
            
            tracker.track_llm_usage(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
    except Exception as e:
        # Don't fail the API call if tracking fails
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to track gas meter usage for LangChain call: {e}")
    
    return response


def track_manual_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_override: Optional[float] = None
) -> None:
    """
    Manually track LLM usage when you have token counts but aren't using the wrapper.
    
    Args:
        model: Model name (e.g., "gpt-4o-mini")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cost_override: Optional manual cost override
    """
    tracker = get_gas_meter_tracker()
    tracker.track_llm_usage(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_override=cost_override
    )
