"""
Script to run the Django application with Uvicorn.
This provides an easy way to start the asynchronous Django server.
"""
import os
import sys
import uvicorn

def main():
    """Run the application with Uvicorn."""
    # Default settings
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = "--no-reload" not in sys.argv

    print(f"Starting server at {host}:{port}")
    uvicorn.run(
        "core.asgi:application",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        workers=1,  # For development, use 1 worker
    )

if __name__ == "__main__":
    main()
