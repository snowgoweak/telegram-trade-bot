import base64

import httpx
from fastapi import APIRouter, HTTPException
from tonutils.client import TonapiClient
from tonutils.wallet import WalletV4R2

from service.app.security import decrypt_private_key

router = APIRouter()


class MyTonClient:
    def __init__(
        self,
        api_key: str = "AG7ABP5LK3VBS2YAAAAIUJCB4HIZCXUKZSYPN5OIARDOZRABG4JFZR3VJQASVZKWFTNHYOQ",
        is_testnet: bool = True,
    ):
        self.api_key = api_key
        self.is_testnet = is_testnet
        self.client = TonapiClient(api_key=self.api_key, is_testnet=self.is_testnet)

    async def create_wallet(self) -> dict:
        """
        Создает новый TON-кошелек с использованием WalletV4R2.
        Возвращает адрес, публичный ключ, мнемонику и зашифрованный приватный ключ.
        Байтовые данные кодируются в base64 для корректной сериализации в JSON.
        При создании кошелек сохраняется в памяти для дальнейшего использования.
        """
        wallet, public_key, private_key, mnemonic = WalletV4R2.create(self.client)
        encoded_public_key = base64.b64encode(public_key).decode("utf-8")
        encoded_private_key = base64.b64encode(private_key).decode("utf-8")
        wallet_address = wallet.address.to_str()
        return {
            "address": wallet_address,
            "public_key": encoded_public_key,
            "mnemonic": mnemonic,
            "private_key": encoded_private_key,
        }

    async def restore_wallet(self, wallet_record) -> WalletV4R2:
        """
        Восстанавливает объект кошелька (WalletV4R2) из данных, хранящихся в БД.
        Расшифровываем сохраненную мнемонику, делим строку по разделителю "; " и используем from_mnemonic.
        """
        decrypted_mnemonic = decrypt_private_key(wallet_record.mnemonic)
        mnemonic_list = decrypted_mnemonic.split("; ")
        wallet_obj, _, _, _ = WalletV4R2.from_mnemonic(self.client, mnemonic_list)
        return wallet_obj

    @staticmethod
    async def swap_ton_to_jetton(
         wallet: WalletV4R2, amount: float, jetton_address: str
    ) -> dict:
        """
        Выполняет своп TON в Jetton.

        :param wallet: Адрес кошелька, из которого выполняется транзакция.
        :param amount: Количество TON для обмена.
        :param jetton_address: Адрес Jetton, в который необходимо обменять.
        :return: Словарь с результатом транзакции (tx_hash и статус).
        """
        try:
            tx_hash = await wallet.stonfi_swap_ton_to_jetton(
                jetton_master_address=jetton_address,
                ton_amount=amount,
                version=2,
            )
            return {"tx_hash": tx_hash, "status": "submitted"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def swap_jetton_to_ton(
        wallet: WalletV4R2,
        amount: float,
        jetton_address: str,
        jetton_decimals: int = 9,
    ) -> dict:
        """
        Выполняет своп Jetton в TON.

        :param wallet: Адрес кошелька, из которого выполняется транзакция.
        :param amount: Количество Jetton для обмена.
        :param jetton_address: Адрес Jetton, который будет обменян на TON.
        :return: Словарь с результатом транзакции (tx_hash и статус).
        """
        try:
            tx_hash = await wallet.stonfi_swap_jetton_to_ton(
                jetton_master_address=jetton_address,
                jetton_amount=amount,
                jetton_decimals=jetton_decimals,
                version=2,
            )
            return {"tx_hash": tx_hash, "status": "submitted"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def check_transaction_status(tx_hash: str) -> str:
        """
        Проверяет статус транзакции по tx_hash, обращаясь к TON API.
        URL: https://tonapi.io/v2/blockchain/transactions/{tx_hash}
        В ответе ожидается JSON с булевыми полями:
          - success
          - aborted
          - destroyed
        Если success==True, возвращается "confirmed".
        Если aborted==True или destroyed==True, возвращается "failed".
        Иначе возвращается "processing".
        """
        url = f"https://tonapi.io/v2/blockchain/transactions/{tx_hash}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        success = data.get("success", False)
        aborted = data.get("aborted", False)
        destroyed = data.get("destroyed", False)

        if success:
            return "executed"
        elif aborted or destroyed:
            return "failed"
        else:
            return "pending"
