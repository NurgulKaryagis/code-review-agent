import os

# Set fake credentials before any module imports so that config/settings.py
# does not raise EnvironmentError during test collection.
os.environ.setdefault("GITHUB_TOKEN", "fake-github-token")
os.environ.setdefault("OPENAI_API_KEY", "fake-openai-key")
