"""
Shared content generation task storage
Moved from main.py to avoid circular imports
"""
CONTENT_GEN_TASKS = {}
CONTENT_GEN_TASK_INDEX = {}

# Max wall-clock time for a content-generation task. If status is still running after this,
# the status endpoint will mark the task as failed so the frontend gets a terminal state.
MAX_CONTENT_GEN_DURATION_SEC = 10 * 60  # 10 minutes



