#!/usr/bin/env python3
"""Startup script for President game backend"""

import os
import uvicorn
from .main import app

def main():
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 Starting President Game Backend on {host}:{port}")
    print(f"📍 Health check available at: http://{host}:{port}/health")
    print(f"🔌 WebSocket endpoint: ws://{host}:{port}/ws")
    
    uvicorn.run(
        "president_engine.main:app",
        host=host,
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )

if __name__ == "__main__":
    main() 