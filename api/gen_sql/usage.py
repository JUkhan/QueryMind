"""Run-level token accounting for the SQL generation agent.

One UsageTracker is attached to each graph run through the run config, so every
LLM call the run makes reports into the same totals: the agent node's call plus
one per get_schema_detail lookup. Aggregating in a callback rather than at the
call sites keeps the numbers right when a turn loops through the tools node more
than once, and means a new call site is counted without being wired up.
"""

import os
import threading
import time

from langchain_core.callbacks import BaseCallbackHandler


def usage_log_level():
    """Read at call time; at import time load_dotenv() may not have run."""
    return os.getenv('GEN_SQL_LOG_USAGE', 'on').strip().lower()


def usage_logging_enabled():
    return usage_log_level() not in ('0', 'off', 'false', 'no')


def usage_logging_verbose():
    """Verbose adds a line per LLM call, which separates the agent turn from
    the schema lookups; the default is one summary line per turn."""
    return usage_log_level() in ('verbose', 'debug')


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def read_usage(response):
    """Return (usage_metadata, model_name) from an LLMResult.

    Chat models hang usage off the generated message. Provider-level
    llm_output is deliberately not used as a fallback: Gemini reports it there
    under different key names (prompt_token_count), which would silently read
    as zeros rather than as an untracked call.
    """
    usage = None
    model = None
    for generations in getattr(response, 'generations', None) or []:
        for generation in generations:
            message = getattr(generation, 'message', None)
            if message is None:
                continue
            metadata = getattr(message, 'response_metadata', None) or {}
            model = model or metadata.get('model_name') or metadata.get('model')
            usage = usage or getattr(message, 'usage_metadata', None)
    if model is None:
        model = (getattr(response, 'llm_output', None) or {}).get('model_name')
    return usage, model


class UsageTracker(BaseCallbackHandler):
    """Accumulates token usage and prompt-cache metrics across one run."""

    def __init__(self, thread_id, label='chat'):
        self.thread_id = thread_id
        self.label = label
        self.calls = 0
        self.untracked_calls = 0
        self.errors = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_read_tokens = 0
        self.cache_write_tokens = 0
        self.reasoning_tokens = 0
        self.trims = 0
        self.trimmed_messages = 0
        self.models = []
        # The sync worker runs one turn at a time, but callbacks are the one
        # place a threaded or async executor would reach this concurrently.
        self._lock = threading.Lock()
        self._started = time.monotonic()

    # -- callbacks ---------------------------------------------------------

    def on_llm_end(self, response, **kwargs):
        usage, model = read_usage(response)
        with self._lock:
            if model and model not in self.models:
                self.models.append(model)
            if not usage:
                # The call still happened and was still billed; a nonzero
                # untracked count is the signal that these totals are partial.
                self.untracked_calls += 1
                return
            self.calls += 1
            input_tokens = _int(usage.get('input_tokens'))
            output_tokens = _int(usage.get('output_tokens'))
            input_details = usage.get('input_token_details') or {}
            output_details = usage.get('output_token_details') or {}
            # input_tokens is the whole prompt including the cached prefix, so
            # cache_read / input_tokens is the hit rate and not double counting.
            cache_read = _int(input_details.get('cache_read'))
            cache_write = _int(input_details.get('cache_creation'))
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.cache_read_tokens += cache_read
            self.cache_write_tokens += cache_write
            self.reasoning_tokens += _int(output_details.get('reasoning'))

        if usage_logging_verbose():
            print(f'USAGE:: call thread={self.thread_id} model={model or "?"} '
                  f'in={input_tokens} out={output_tokens} '
                  f'cache_read={cache_read} cache_write={cache_write}')

    def on_llm_error(self, error, **kwargs):
        with self._lock:
            self.errors += 1

    # -- run events --------------------------------------------------------

    def note_trim(self, dropped):
        """Record that history was trimmed.

        Trimming moves the cacheable prompt prefix, so the cache hit rate
        collapses on exactly these turns. Without the trim count alongside it,
        that drop looks random.
        """
        if dropped <= 0:
            return
        with self._lock:
            self.trims += 1
            self.trimmed_messages += dropped

    # -- reporting ---------------------------------------------------------

    def summary(self):
        with self._lock:
            hit_rate = self.cache_read_tokens / self.input_tokens if self.input_tokens else 0.0
            return {
                'thread_id': self.thread_id,
                'label': self.label,
                'calls': self.calls,
                'untracked_calls': self.untracked_calls,
                'errors': self.errors,
                'input_tokens': self.input_tokens,
                'output_tokens': self.output_tokens,
                'total_tokens': self.input_tokens + self.output_tokens,
                'cache_read_tokens': self.cache_read_tokens,
                'cache_write_tokens': self.cache_write_tokens,
                'cache_hit_rate': round(hit_rate, 4),
                'reasoning_tokens': self.reasoning_tokens,
                'trims': self.trims,
                'trimmed_messages': self.trimmed_messages,
                'models': list(self.models),
                'elapsed_seconds': round(time.monotonic() - self._started, 3),
            }

    def log(self):
        """Emit one parseable line for the run and return the summary.

        Call this from a finally block: a turn that failed part way through
        still spent tokens, and those are the turns worth seeing.
        """
        stats = self.summary()
        if not usage_logging_enabled():
            return stats
        if not (stats['calls'] or stats['untracked_calls'] or stats['errors']):
            return stats
        print(
            f"USAGE:: {stats['label']} thread={stats['thread_id']} "
            f"calls={stats['calls']} in={stats['input_tokens']} "
            f"out={stats['output_tokens']} total={stats['total_tokens']} "
            f"cache_read={stats['cache_read_tokens']} "
            f"cache_write={stats['cache_write_tokens']} "
            f"cache_hit={stats['cache_hit_rate'] * 100:.1f}% "
            f"reasoning={stats['reasoning_tokens']} trims={stats['trims']} "
            f"trimmed_msgs={stats['trimmed_messages']} "
            f"untracked={stats['untracked_calls']} errors={stats['errors']} "
            f"model={'+'.join(stats['models']) or '?'} "
            f"elapsed={stats['elapsed_seconds']}s")
        return stats


def find_tracker(config):
    """Pull the run's UsageTracker back out of the config a graph node receives.

    LangGraph hands nodes a CallbackManager rather than the list that went into
    thread_config(), so unwrap .handlers when it is there.
    """
    callbacks = (config or {}).get('callbacks')
    handlers = getattr(callbacks, 'handlers', callbacks) or []
    for handler in handlers:
        if isinstance(handler, UsageTracker):
            return handler
    return None
