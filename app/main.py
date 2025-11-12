from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routes import email_routes
from app.services.gmail_service import get_gmail_service
from app.services.extraction_service import get_extraction_service
from app.services.label_service import get_label_service
from app.services.pdf_service import get_pdf_service
from app.services.classification_service import get_classification_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    gmail_service = get_gmail_service()
    get_extraction_service()
    get_label_service()
    get_pdf_service()
    get_classification_service()
    
    if gmail_service.load_credentials():
        if gmail_service.is_authenticated():
            try:
                gmail_service.build_service()
            except Exception as e:
                print(f"Error al construir servicio Gmail: {e}")
    
    yield


app = FastAPI(
    title="Gmail Analyzer API",
    version="0.1.0",
    lifespan=lifespan
)
app.include_router(email_routes.router)


@app.get("/health")
def health():
    return {"status": "ok"}

