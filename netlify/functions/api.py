"""
Netlify Functions ASGI entrypoint for FastAPI.
Adapts ASGI requests to AWS Lambda / Netlify Serverless format via Mangum.
Strips Netlify function path prefixes so FastAPI routes match cleanly.
"""

from mangum import Mangum
from backend.app.main import app

# Initialize Mangum with lifespan disabled for serverless environment
_mangum_handler = Mangum(app, lifespan="off")


def handler(event, context):
    """
    Netlify Functions Lambda handler.
    Normalizes path prefixes such as /.netlify/functions/api so FastAPI receives clean routes.
    """
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
