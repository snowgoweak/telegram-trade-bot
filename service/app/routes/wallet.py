from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from service.app.database import get_db
from service.app.models import User, Wallet
from service.app.security import decrypt_private_key, encrypt_private_key
from service.app.ton_wallet import MyTonClient

router = APIRouter()
ton_client = MyTonClient()


@router.get("/wallet/create/{telegram_user_id}")
async def create_or_get_wallet(
    telegram_user_id: str, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalars().first()
    if not user:
        user = User(telegram_user_id=telegram_user_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    w_result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = w_result.scalars().first()

    if not wallet:
        wallet_data = await ton_client.create_wallet()
        encrypted_key = encrypt_private_key(wallet_data["private_key"])
        encrypted_mnemonic = encrypt_private_key(", ".join(wallet_data["mnemonic"]))
        wallet = Wallet(
            address=wallet_data["address"],
            private_key=encrypted_key,
            mnemonic=encrypted_mnemonic,
            balance="0",
            owner=user,
        )
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)

    return {
        "address": wallet.address,
    }


@router.get("/wallet/export/{telegram_user_id}")
async def export_wallet(telegram_user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="The user was not found")

    w_result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = w_result.scalars().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    return {
        "address": wallet.address,
        "mnemonic": decrypt_private_key(wallet.mnemonic),
    }
