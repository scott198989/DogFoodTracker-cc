"""
Vercel serverless function entry point.
This file exposes the FastAPI app for Vercel deployment.
"""

from app.main import app

# Vercel looks for an 'app' variable or a 'handler' function
# FastAPI apps work directly with Vercel's Python runtime
