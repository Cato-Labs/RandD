"""Vantage AI FastAPI backend."""

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

# Load backend/.env first, then fall back to the repo-root .env (both
# gitignored) so provider credentials (GOOGLE_API_KEY, OPENAI_*, AWS_*) are
# set within the project without ever being committed.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
_root_env = Path(__file__).resolve().parent.parent.parent / ".env"
for _name, _value in dotenv_values(_root_env).items():
    # Backend-specific non-empty values take precedence. Empty placeholders
    # (including the Slack keys documented in backend/.env) fall back to the
    # root developer environment without masking it.
    if _value is not None and not os.getenv(_name):
        os.environ[_name] = _value

# botocore only resolves the default region from AWS_DEFAULT_REGION; bridge it
# from AWS_REGION so every boto3 client (Bedrock KB memory, Nova) gets a region.
if os.getenv("AWS_REGION") and not os.getenv("AWS_DEFAULT_REGION"):
    os.environ["AWS_DEFAULT_REGION"] = os.environ["AWS_REGION"]

# Slack uses rotating tokens (~12h expiry): refresh the bot token at startup so
# the slack tools always initialize with a live token.
from app.slack_token import ensure_fresh_bot_token  # noqa: E402

if os.getenv("VANTAGE_SKIP_SLACK_REFRESH") != "1":
    ensure_fresh_bot_token()
