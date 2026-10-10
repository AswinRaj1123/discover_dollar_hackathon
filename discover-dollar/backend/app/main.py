import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import DEFAULT_DATABASE_PATH, Database, serialize_row


def create_app(
    database_path: Path | str = DEFAULT_DATABASE_PATH,
) -> FastAPI:
    database = Database(database_path)

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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
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

    return app


app = create_app()
