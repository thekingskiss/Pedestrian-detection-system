"""
Structured logging setup. Kept simple (stdlib logging + JSON-ish formatter)
so it works the same in a bare-metal deployment or inside a container where
stdout is collected by the platform's log pipeline.
"""
import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
        )
    )
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
