from fastapi import FastAPI

app = FastAPI(
    title="DocGuard AI",
    description="Multimodal document compliance and audit reviewer",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "healthy"}
