from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import engine

from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.customers.router import router as customers_router
from app.modules.products.router import router as products_router
from app.modules.plans.router import router as plans_router
from app.modules.taxes.router import router as taxes_router
from app.modules.discounts.router import router as discounts_router
from app.modules.quotation_templates.router import router as quotation_templates_router
from app.modules.quotations.router import router as quotations_router


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Subscription and recurring billing management platform."
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(customers_router)
app.include_router(products_router)
app.include_router(plans_router)
app.include_router(taxes_router)
app.include_router(discounts_router)
app.include_router(quotation_templates_router)
app.include_router(quotations_router)


@app.get("/health", tags=["Health"])
def health_check():

    return {
        "status": "ok",
        "service": "brightloop-api"
    }


@app.get("/health/ready", tags=["Health"])
def readiness_check():

    try:

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "ready",
            "database": "connected"
        }

    except SQLAlchemyError:

        raise HTTPException(
            status_code=503,
            detail="Database is unavailable"
        )
