from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.documents import router as documents_router
from app.core.database import initialize_database
from app.core.logging import setup_logging

setup_logging()
initialize_database()


app = FastAPI(
    title="NeoStats Document Intelligence API",
    version="1.0.0",
)


# Allow the local frontend to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(documents_router)


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "service": "neostats-document-intelligence",
    }