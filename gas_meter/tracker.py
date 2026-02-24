"""
Gas Meter Tracker - Tracks LLM token usage and costs
"""

import os
import time
from datetime import datetime
from typing import Dict, Optional
from threading import Lock
from dotenv import load_dotenv

load_dotenv()

# OpenAI pricing (per 1M tokens) as of 2024
# gpt-4o-mini: $0.15/$0.60 per 1M tokens (input/output)
OPENAI_PRICING = {
    "gpt-4o-mini": {
        "input": 0.15 / 1_000_000,  # per token
        "output": 0.60 / 1_000_000,  # per token
    },
    "gpt-4o": {
        "input": 2.50 / 1_000_000,
        "output": 10.00 / 1_000_000,
    },
    "gpt-4": {
        "input": 30.00 / 1_000_000,
        "output": 60.00 / 1_000_000,
    },
    "gpt-3.5-turbo": {
        "input": 0.50 / 1_000_000,
        "output": 1.50 / 1_000_000,
    },
    # Default fallback pricing
    "default": {
        "input": 0.15 / 1_000_000,
        "output": 0.60 / 1_000_000,
    }
}

# EC2 cost tracking - with safe parsing
def _safe_float(value: str, default: float) -> float:
    """Safely parse float from environment variable."""
    try:
        return float(value) if value else default
    except (ValueError, TypeError):
        return default

def _get_ec2_rate() -> float:
    try:
        from env_override import get_effective_env
        return _safe_float(get_effective_env("EC2_HOURLY_RATE_USD", "0.0416"), 0.0416)
    except ImportError:
        return _safe_float(os.getenv("EC2_HOURLY_RATE_USD", "0.0416"), 0.0416)


def _get_ec2_utilization() -> float:
    try:
        from env_override import get_effective_env
        return _safe_float(get_effective_env("EC2_UTILIZATION_FACTOR", "1.0"), 1.0)
    except ImportError:
        return _safe_float(os.getenv("EC2_UTILIZATION_FACTOR", "1.0"), 1.0)


class GasMeterTracker:
    """
    Thread-safe cost tracker for LLM tokens and EC2 infrastructure costs.
    """
    
    def __init__(self):
        self._lock = Lock()
        self._start_time = time.time()
        self._llm_tokens_used = 0
        self._llm_cost_usd = 0.0
        self._session_start = datetime.now().isoformat()
        
    def track_llm_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_override: Optional[float] = None
    ) -> None:
        """
        Track LLM token usage and calculate cost.
        
        Args:
            model: Model name (e.g., "gpt-4o-mini")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_override: Optional manual cost override (if provided, skips calculation)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        with self._lock:
            total_tokens = input_tokens + output_tokens
            self._llm_tokens_used += total_tokens
            
            if cost_override is not None:
                self._llm_cost_usd += cost_override
                logger.info(f"💰 Gas Meter: Tracked {total_tokens} tokens (override cost: ${cost_override:.6f})")
            else:
                # Calculate cost based on model pricing
                pricing = OPENAI_PRICING.get(model, OPENAI_PRICING["default"])
                input_cost = input_tokens * pricing["input"]
                output_cost = output_tokens * pricing["output"]
                cost = input_cost + output_cost
                self._llm_cost_usd += cost
                logger.info(f"💰 Gas Meter: Tracked {total_tokens} tokens ({input_tokens} in, {output_tokens} out) for {model} = ${cost:.6f}")
            
            logger.info(f"📊 Gas Meter: Total tokens: {self._llm_tokens_used}, Total cost: ${self._llm_cost_usd:.6f}")
    
    def get_current_costs(self) -> Dict:
        """
        Get current cost metrics.
        
        Returns:
            Dictionary with cost metrics:
            {
                "llm_tokens_used": int,
                "llm_cost_usd": float,
                "ec2_cost_usd": float,
                "total_cost_usd": float,
                "last_updated": str (ISO format),
                "session_start": str (ISO format)
            }
        """
        with self._lock:
            # Calculate EC2 cost based on runtime (Admin > Environment Variables or process env)
            runtime_seconds = time.time() - self._start_time
            runtime_hours = runtime_seconds / 3600.0
            ec2_cost = runtime_hours * _get_ec2_rate() * _get_ec2_utilization()
            
            total_cost = self._llm_cost_usd + ec2_cost
            
            return {
                "llm_tokens_used": self._llm_tokens_used,
                "llm_cost_usd": round(self._llm_cost_usd, 6),
                "ec2_cost_usd": round(ec2_cost, 6),
                "total_cost_usd": round(total_cost, 6),
                "last_updated": datetime.now().isoformat(),
                "session_start": self._session_start
            }
    
    def reset(self) -> None:
        """Reset all counters (for new session)."""
        with self._lock:
            self._start_time = time.time()
            self._llm_tokens_used = 0
            self._llm_cost_usd = 0.0
            self._session_start = datetime.now().isoformat()


# Global singleton instance
_gas_meter_tracker: Optional[GasMeterTracker] = None


def get_gas_meter_tracker() -> GasMeterTracker:
    """Get or create the global gas meter tracker instance."""
    global _gas_meter_tracker
    if _gas_meter_tracker is None:
        _gas_meter_tracker = GasMeterTracker()
    return _gas_meter_tracker
