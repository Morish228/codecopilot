import os

# Avoid console span export errors during pytest teardown.
os.environ.setdefault("OTEL_ENABLED", "true")
os.environ.setdefault("OTEL_EXPORTER", "none")
