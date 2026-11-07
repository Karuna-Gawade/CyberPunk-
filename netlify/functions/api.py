"""
Netlify Functions ASGI entrypoint for FastAPI.
Adapts ASGI requests to AWS Lambda / Netlify Serverless format via Mangum.
Strips Netlify function path prefixes so FastAPI routes match cleanly.
"""

import os
import sys
import traceback
from pathlib import Path

# Add project root and netlify/functions to sys.path so 'backend' package is importable
FILE_PATH = Path(__file__).resolve()
FUNCTIONS_DIR = FILE_PATH.parent
NETLIFY_DIR = FUNCTIONS_DIR.parent
PROJECT_ROOT = NETLIFY_DIR.parent

for p in (PROJECT_ROOT, NETLIFY_DIR, FUNCTIONS_DIR):
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

# Also check AWS Lambda task root (/var/task)
task_root = os.environ.get("LAMBDA_TASK_ROOT")
if task_root and task_root not in sys.path:
    sys.path.insert(0, task_root)

# Mark serverless environment
os.environ["NETLIFY"] = "true"

try:
    from mangum import Mangum
    from backend.app.main import app
    _mangum_handler = Mangum(app, lifespan="off")
    _init_error = None
except Exception as e:
    _mangum_handler = None
    _init_error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"


def handler(event, context):
    """
    Netlify Functions Lambda handler.
    Normalizes path prefixes such as /.netlify/functions/api so FastAPI receives clean routes.
    """
    if _init_error is not None:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": f'{{"error": "Function initialization error", "detail": {repr(_init_error)}}}',
        }

    prefix = "/.netlify/functions/api"

    # Normalize top-level path and rawPath
    for key in ("path", "rawPath"):
        if key in event and isinstance(event[key], str) and event[key].startswith(prefix):
            event[key] = event[key][len(prefix):] or "/"

    # Normalize requestContext paths
    if "requestContext" in event and isinstance(event["requestContext"], dict):
        rc = event["requestContext"]
        if "http" in rc and isinstance(rc["http"], dict):
            p = rc["http"].get("path", "")
            if p.startswith(prefix):
                rc["http"]["path"] = p[len(prefix):] or "/"
        if "path" in rc and isinstance(rc["path"], str) and rc["path"].startswith(prefix):
            rc["path"] = rc["path"][len(prefix):] or "/"

    return _mangum_handler(event, context)
