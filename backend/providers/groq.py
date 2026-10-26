"""Groq tool calls are validated as a complete response before Strands sees them."""
import asyncio
import json
import logging
import openai
from strands.models.openai import OpenAIModel

logger = logging.getLogger(__name__)

class ToolCallFormatError(RuntimeError):
    pass

class GroqModel(OpenAIModel):
    def __init__(self, **kwargs):
        # Prevent partially delivered tool calls from reaching the executor.
        super().__init__(**{**kwargs, 'stream': False})

    def _format_non_streaming_response(self, response):
        choice = response.choices[0]
        for call in getattr(choice.message, 'tool_calls', None) or []:
            try:
                arguments = json.loads(call.function.arguments)
            except (ValueError, TypeError) as exc:
                raise ToolCallFormatError('Provider returned malformed tool arguments') from exc
            if not isinstance(arguments, dict):
                raise ToolCallFormatError('Provider tool arguments must be a JSON object')
        return super()._format_non_streaming_response(response)

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        for attempt in range(2):
            try:
                # Retry only this uncommitted model response, never an agent,
                # workflow, or tool. No events are released until it is valid.
                chunks = [chunk async for chunk in super().stream(messages, tool_specs, system_prompt, **kwargs)]
            except (openai.APIError, ToolCallFormatError) as exc:
                code = getattr(exc, 'code', None)
                if not isinstance(exc, ToolCallFormatError) and code != 'tool_use_failed':
                    raise
                if attempt:
                    raise ToolCallFormatError('Model returned invalid tool arguments twice; this response executed no tools. Review the run before retrying.') from exc
                logger.warning('Invalid model tool response; retrying this response once without executing tools')
                await asyncio.sleep(0.25)
            else:
                for chunk in chunks:
                    yield chunk
                return
