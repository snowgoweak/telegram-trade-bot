import uvicorn
from database import engine
from fastapi import FastAPI
from models import Base
from routes.order import router as order_router
from routes.wallet import router as wallet_router

from service.app.scheduler import start_scheduler

app = FastAPI(title="TON Wallet Service")
app.include_router(wallet_router, prefix="/api", tags=["Wallet"])
app.include_router(order_router, prefix="/api", tags=["Order"])


@app.on_event("startup")
async def startup_event():
    scheduler = await start_scheduler()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.on_event("shutdown")
async def shutdown_event(): ...


if __name__ == "__main__":
    uvicorn.run("service.app.main:app", host="0.0.0.0", port=8000, reload=True)
