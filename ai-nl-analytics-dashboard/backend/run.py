import uvicorn

if __name__ == "__main__":
    # Run the FastAPI app using Uvicorn
    # timeout_keep_alive=65 prevents 'ECONNRESET socket hang up' errors 
    # when Next.js API rewrites proxy requests to this backend.
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        timeout_keep_alive=65
    )
