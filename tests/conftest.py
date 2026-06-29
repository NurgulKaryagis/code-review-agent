import os

# Fake credentials so config/settings.py doesn't raise EnvironmentError during collection.
os.environ.setdefault("GITHUB_TOKEN", "fake-github-token")
os.environ.setdefault("OPENAI_API_KEY", "fake-openai-key")
os.environ.setdefault("MODEL_NAME", "gpt-4o-mini")