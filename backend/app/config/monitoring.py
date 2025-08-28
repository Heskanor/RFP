import os
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

langfuse = Langfuse()

langfuse_handler = CallbackHandler(
    tags=[os.getenv("LANGFUSE_TRACE_ENV"), "MagicRFP"]
)
