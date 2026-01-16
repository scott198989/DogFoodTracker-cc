"""
Vercel serverless function entry point.
This file exposes the FastAPI app for Vercel deployment.
"""

import sys
from pathlib import Path

# Add the project root to Python path for imports
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from app.main import app

# Vercel looks for an 'app' variable or a 'handler' function
# FastAPI apps work directly with Vercel's Python runtime
