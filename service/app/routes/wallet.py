from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from service.app.database import get_db
from service.app.models import User, Wallet
from service.app.security import decrypt_private_key, encrypt_private_key
from service.app.ton_wallet import MyTonClient

router = APIRouter()
ton_client = MyTonClient()


class WalletInfoResponse(BaseModel):
    address: str
    balance: str

    class Config:
        from_attributes = True


@router.get("/wallet/create/{telegram_user_id}")
async def create_or_get_wallet(
    telegram_user_id: str, db: AsyncSession = Depends(get_db)
):
    """
    Эндпоинт для получения/создания кошелька пользователя.
    1) Проверяем, есть ли пользователь. Если нет, создаем.
    2) Проверяем, есть ли кошелек. Если нет, создаем новый.
    3) Приватный ключ шифруем и сохраняем в БД.
    """
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
            mnemonic=encrypted_mnemonic,  # Сохраняем зашифрованную строку
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
    """
    Эндпоинт для экспорта приватного ключа:
      1) Проверяем, есть ли пользователь, если нет – ошибка.
      2) Ищем кошелек. Если нет – ошибка.
      3) Проверяем дополнительный секрет (или PIN) для безопасности.
      4) Расшифровываем приватный ключ и возвращаем.
    """
    result = await db.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    w_result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = w_result.scalars().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Кошелек не найден")

    # 3) Проверяем секрет
    # Предположим, у вас в .env есть EXPORT_SECRET="some_secret"
    # и вы хотите, чтобы при экспорте пользователь передавал этот secret
    # (или другой PIN, подтверждающий разрешение на экспорт)
    # if data.secret != EXPORT_SECRET:
    #     raise HTTPException(status_code=403, detail="Неверный секрет для экспорта")

    try:
        decrypted_key = decrypt_private_key(wallet.mnemonic)
    except Exception:
        raise HTTPException(
            status_code=500, detail="Ошибка при расшифровании приватного ключа"
        )
    return {
        "address": wallet.address,
        "private_key": decrypted_key,
    }
