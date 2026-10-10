import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, model_validator

from .database import DEFAULT_DATABASE_PATH, DEFAULT_SEED_PATH, Database, serialize_row
from .service import DomainError, ShiftSwapService


DEFAULT_FRONTEND_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://shiftswap-discover-dollar.vercel.app",
]


def frontend_origins() -> list[str]:
    configured = os.getenv("FRONTEND_URLS") or os.getenv("FRONTEND_URL")
    configured_origins = (
        [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
        if configured
        else []
    )
    return list(dict.fromkeys(DEFAULT_FRONTEND_ORIGINS + configured_origins))


class ActorRequest(BaseModel):
    actor_id: str | None = None
    staff_id: str | None = None

    @model_validator(mode="after")
    def has_actor(self):
        if not self.actor_id and not self.staff_id:
            raise ValueError("actor_id is required")
        return self

    @property
    def actor(self) -> str:
        return self.actor_id or self.staff_id  # type: ignore[return-value]


class ListingRequest(ActorRequest):
    shift_id: str


def create_app(
    database_path: Path | str = DEFAULT_DATABASE_PATH,
    seed_path: Path | str = DEFAULT_SEED_PATH,
) -> FastAPI:
    database = Database(database_path, seed_path)
    service = ShiftSwapService(database)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        database.initialize()
        yield

    app = FastAPI(
        title="ShiftSwap API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.database = database
    app.state.service = service

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, error: DomainError):
        body = {"detail": error.message}
        if error.reasons:
            body["reasons"] = error.reasons
        return JSONResponse(status_code=error.status_code, content=body)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=frontend_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    @app.get("/health")
    def health_check():
        return {"status": "ok", "database": "sqlite"}

    @app.get("/api/staff")
    def list_staff():
        return {"staff": [serialize_row("staff", row) for row in database.fetch_all("staff")]}

    @app.get("/api/shifts")
    def list_shifts():
        return {"shifts": database.fetch_all("shifts")}

    @app.get("/api/listings")
    def list_listings():
        return {
            "listings": [
                serialize_row("listings", row)
                for row in database.fetch_all("listings")
            ]
        }

    @app.get("/api/history")
    def list_history():
        return {
            "history": [
                serialize_row("action_history", row)
                for row in database.fetch_all("action_history")
            ]
        }

    @app.post("/api/shifts/{shift_id}/listings", status_code=201)
    def post_listing(shift_id: str, request: ActorRequest):
        return service.post(request.actor, shift_id)

    @app.post("/api/listings", status_code=201)
    def create_listing(request: ListingRequest):
        return service.post(request.actor, request.shift_id)

    @app.post("/api/listings/{listing_id}/withdraw")
    def withdraw_listing(listing_id: int, request: ActorRequest):
        return service.withdraw(request.actor, listing_id)

    @app.post("/api/listings/{listing_id}/claim")
    def claim_listing(listing_id: int, request: ActorRequest):
        return service.claim(request.actor, listing_id)

    @app.post("/api/listings/{listing_id}/unclaim")
    def unclaim_listing(listing_id: int, request: ActorRequest):
        return service.unclaim(request.actor, listing_id)

    @app.post("/api/listings/{listing_id}/approve")
    def approve_listing(listing_id: int, request: ActorRequest):
        return service.approve(request.actor, listing_id)

    @app.post("/api/listings/{listing_id}/reject")
    def reject_listing(listing_id: int, request: ActorRequest):
        return service.reject(request.actor, listing_id)

    return app


app = create_app()
