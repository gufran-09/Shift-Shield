"""AWS Lambda entry point for API Gateway HTTP API."""
from mangum import Mangum

from .main import app

handler = Mangum(app, lifespan="off")
