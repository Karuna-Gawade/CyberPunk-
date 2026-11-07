"""
Netlify Functions ASGI entrypoint for FastAPI.
Adapts ASGI requests to AWS Lambda / Netlify Serverless format via Mangum.
"""

from mangum import Mangum
from backend.app.main import app

# Wrap FastAPI with Mangum
handler = Mangum(app, lifespan="off")
