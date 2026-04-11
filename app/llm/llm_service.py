"""
LLM Service
-----------
Calls Claude 3 Sonnet on Amazon Bedrock.
Provides:
  - generate()        — blocking, returns full text
  - generate_stream() — async generator, yields text chunks for SSE streaming
"""
import json
from typing import AsyncGenerator, List

from app.llm.bedrock_client import get_bedrock_runtime
from app.core.config import settings
from app.utils.logger import logger


def generate(prompt: str, max_tokens: int = 1024) -> str:
    """
    Send a prompt to Claude 3 Sonnet on Bedrock and return the response text.

    Args:
        prompt:     The fully-rendered prompt string (use prompts.py templates).
        max_tokens: Maximum tokens in the response (default 1024).

    Returns:
        The model's text response as a plain string.
    """
    client = get_bedrock_runtime()

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }

    prompt_preview = prompt[:300] + ("..." if len(prompt) > 300 else "")
    logger.info(
        f"[BEDROCK LLM] → model={settings.BEDROCK_MODEL_ID} "
        f"max_tokens={max_tokens} prompt_length={len(prompt)}"
    )
    logger.info(f"[BEDROCK LLM] → prompt_preview={prompt_preview!r}")

    try:
        response = client.invoke_model(
            modelId=settings.BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        result = json.loads(response["body"].read())
        text = result["content"][0]["text"]
        usage = result.get("usage", {})
        logger.info(
            f"[BEDROCK LLM] ← model={settings.BEDROCK_MODEL_ID} "
            f"input_tokens={usage.get('input_tokens','?')} "
            f"output_tokens={usage.get('output_tokens','?')} "
            f"response_length={len(text)}"
        )
        logger.info(f"[BEDROCK LLM] ← response_preview={text[:300]!r}")
        return text.strip()

    except Exception as e:
        logger.error(f"[BEDROCK LLM] ✗ Bedrock invocation failed: {type(e).__name__}: {e}")
        raise


async def generate_stream(prompt: str, max_tokens: int = 1024) -> AsyncGenerator[str, None]:
    """
    Stream a response from Claude on Bedrock using invoke_model_with_response_stream.
    Yields plain text chunks as they arrive — suitable for SSE.

    The synchronous Bedrock stream iteration runs in a thread pool executor and
    pushes chunks into an asyncio.Queue so the event loop is never blocked.
    This allows other requests to be served concurrently while Claude is generating.

    Args:
        prompt:     The fully-rendered prompt string.
        max_tokens: Maximum tokens in the response (default 1024).

    Yields:
        str — incremental text chunks from the model.
    """
    import asyncio

    _SENTINEL = object()  # signals end of stream

    client = get_bedrock_runtime()

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    })

    logger.info(
        f"[BEDROCK STREAM] → model={settings.BEDROCK_MODEL_ID} "
        f"max_tokens={max_tokens} prompt_length={len(prompt)}"
    )

    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def _stream_in_thread():
        """
        Runs entirely in a thread. Calls Bedrock, iterates the sync stream,
        and puts text chunks (or exceptions) into the asyncio queue.
        Never touches the event loop directly.
        """
        try:
            response = client.invoke_model_with_response_stream(
                modelId=settings.BEDROCK_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            stream = response.get("body")
            if not stream:
                logger.warning("[BEDROCK STREAM] Empty stream body returned")
                return

            for event in stream:
                chunk = event.get("chunk")
                if not chunk:
                    continue
                raw = chunk.get("bytes", b"")
                if not raw:
                    continue
                try:
                    data = json.loads(raw.decode("utf-8"))
                except Exception:
                    continue

                event_type = data.get("type", "")

                if event_type == "content_block_delta":
                    text = data.get("delta", {}).get("text", "")
                    if text:
                        loop.call_soon_threadsafe(queue.put_nowait, text)

                elif event_type == "message_stop":
                    logger.info("[BEDROCK STREAM] ← stream complete")
                    break

                elif event_type == "error":
                    error_msg = data.get("error", {}).get("message", "Unknown streaming error")
                    logger.error(f"[BEDROCK STREAM] ✗ {error_msg}")
                    loop.call_soon_threadsafe(
                        queue.put_nowait, Exception(error_msg)
                    )
                    return

        except Exception as exc:
            logger.error(f"[BEDROCK STREAM] ✗ thread error: {exc}")
            loop.call_soon_threadsafe(queue.put_nowait, exc)
        finally:
            # Always signal completion
            loop.call_soon_threadsafe(queue.put_nowait, _SENTINEL)

    # Start the blocking stream in a background thread
    loop.run_in_executor(None, _stream_in_thread)

    # Drain the queue asynchronously — event loop stays free
    while True:
        item = await queue.get()
        if item is _SENTINEL:
            break
        if isinstance(item, Exception):
            yield f"\n[Error: {item}]"
            break
        yield item
