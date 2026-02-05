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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🔍 Gas Meter: Tracking OpenAI call for model {model}")
        
        if hasattr(response, 'usage'):
            usage = response.usage
            if usage:
                input_tokens = getattr(usage, 'prompt_tokens', 0) or 0
                output_tokens = getattr(usage, 'completion_tokens', 0) or 0
                
                logger.info(f"✅ Gas Meter: Extracted tokens - input: {input_tokens}, output: {output_tokens}")
                
                # Track the usage
                tracker.track_llm_usage(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
                logger.info(f"✅ Gas Meter: Tracked {input_tokens + output_tokens} tokens for {model}")
            else:
                logger.warning(f"⚠️ Gas Meter: Response has usage attribute but it's None/empty")
        elif hasattr(response, 'choices') and len(response.choices) > 0:
            # Try to get usage from response object directly
            if hasattr(response, 'usage'):
                usage = response.usage
                input_tokens = getattr(usage, 'prompt_tokens', 0) or 0
                output_tokens = getattr(usage, 'completion_tokens', 0) or 0
                logger.info(f"✅ Gas Meter: Extracted tokens from choices path - input: {input_tokens}, output: {output_tokens}")
                tracker.track_llm_usage(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
            else:
                logger.warning(f"⚠️ Gas Meter: Response has choices but no usage attribute. Response type: {type(response)}")
        else:
            logger.warning(f"⚠️ Gas Meter: Response doesn't have expected structure. Type: {type(response)}, has usage: {hasattr(response, 'usage')}, has choices: {hasattr(response, 'choices')}")
    except Exception as e:
        # Don't fail the API call if tracking fails
        logger.error(f"❌ Gas Meter: Failed to track usage: {e}", exc_info=True)
    
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
    import logging
    logger = logging.getLogger(__name__)
    
    # Make the LangChain call with callbacks to capture token usage
    try:
        from langchain_core.callbacks import CallbackManager
        from langchain_core.tracers import LangChainTracer
        
        # Create a callback manager to capture token usage
        callbacks = []
        token_usage_data = {}
        
        class TokenUsageCallback:
            def on_llm_end(self, response, **kwargs):
                if hasattr(response, 'llm_output') and response.llm_output:
                    token_usage = response.llm_output.get('token_usage', {})
                    token_usage_data.update(token_usage)
        
        callback = TokenUsageCallback()
        callbacks.append(callback)
        
        # Invoke with callbacks
        response = llm.invoke(prompt, *args, config={"callbacks": callbacks}, **kwargs)
    except Exception as callback_error:
        logger.warning(f"⚠️ Gas Meter: Could not set up callbacks, using direct invoke: {callback_error}")
        response = llm.invoke(prompt, *args, **kwargs)
        token_usage_data = {}
    
    # Extract token usage from LangChain response
    try:
        logger.info(f"🔍 Gas Meter: Tracking LangChain call for model {model}")
        
        # First, try to get from callback data
        if token_usage_data:
            input_tokens = token_usage_data.get('prompt_tokens', 0) or 0
            output_tokens = token_usage_data.get('completion_tokens', 0) or 0
            
            if input_tokens > 0 or output_tokens > 0:
                logger.info(f"✅ Gas Meter: Extracted tokens from callback - input: {input_tokens}, output: {output_tokens}")
                tracker.track_llm_usage(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
                return response
        
        # LangChain responses have response_metadata with token usage
        if hasattr(response, 'response_metadata'):
            metadata = response.response_metadata
            logger.info(f"🔍 Gas Meter: Found response_metadata: {metadata}")
            if metadata and 'token_usage' in metadata:
                token_usage = metadata['token_usage']
                input_tokens = token_usage.get('prompt_tokens', 0) or 0
                output_tokens = token_usage.get('completion_tokens', 0) or 0
                
                logger.info(f"✅ Gas Meter: Extracted LangChain tokens - input: {input_tokens}, output: {output_tokens}")
                
                tracker.track_llm_usage(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
                logger.info(f"✅ Gas Meter: Tracked {input_tokens + output_tokens} tokens for {model}")
                return response
            else:
                logger.warning(f"⚠️ Gas Meter: response_metadata exists but no token_usage. Metadata keys: {list(metadata.keys()) if metadata else 'None'}")
        
        # Alternative: check for usage_metadata attribute
        if hasattr(response, 'usage_metadata'):
            usage_meta = response.usage_metadata
            input_tokens = getattr(usage_meta, 'input_tokens', 0) or 0
            output_tokens = getattr(usage_meta, 'output_tokens', 0) or 0
            
            logger.info(f"✅ Gas Meter: Extracted tokens from usage_metadata - input: {input_tokens}, output: {output_tokens}")
            
            tracker.track_llm_usage(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            return response
        
        # Fallback: Try to estimate tokens from content length (rough approximation)
        # This is not accurate but better than nothing
        if hasattr(response, 'content'):
            content_length = len(response.content)
            # Rough estimate: ~4 characters per token
            estimated_output_tokens = max(1, content_length // 4)
            estimated_input_tokens = max(1, len(str(prompt)) // 4)
            
            logger.warning(f"⚠️ Gas Meter: No token usage found, estimating from content length. Input: ~{estimated_input_tokens}, Output: ~{estimated_output_tokens}")
            logger.warning(f"⚠️ Gas Meter: Response type: {type(response)}, attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")
            
            # Only track if we have reasonable estimates
            if estimated_input_tokens > 0 and estimated_output_tokens > 0:
                tracker.track_llm_usage(
                    model=model,
                    input_tokens=estimated_input_tokens,
                    output_tokens=estimated_output_tokens
                )
                logger.info(f"✅ Gas Meter: Tracked estimated tokens for {model}")
        else:
            logger.warning(f"⚠️ Gas Meter: LangChain response doesn't have expected structure. Type: {type(response)}, has response_metadata: {hasattr(response, 'response_metadata')}, has usage_metadata: {hasattr(response, 'usage_metadata')}, has content: {hasattr(response, 'content')}")
            
    except Exception as e:
        # Don't fail the API call if tracking fails
        logger.error(f"❌ Gas Meter: Failed to track LangChain usage: {e}", exc_info=True)
    
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
