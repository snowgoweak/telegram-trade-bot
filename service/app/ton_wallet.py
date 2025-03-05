import base64

import httpx
from fastapi import HTTPException
from tonutils.client import TonapiClient
from tonutils.jetton.dex.stonfi.v2.pton.constants import PTONAddresses
from tonutils.utils import to_nano
from tonutils.wallet import WalletV4R2

from service.app.config import settings
from service.app.schemas import OrderStatus, OrderType
from service.app.security import decrypt_private_key


class MyTonClient:
    def __init__(
        self,
        api_key: str = settings.TON_API_KEY,
        is_testnet: bool = False,
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
        mnemonic_list = decrypted_mnemonic.split(", ")
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
            return OrderStatus.EXECUTED.value
        elif aborted or destroyed:
            return OrderStatus.FAILED.value
        else:
            return OrderStatus.PENDING.value

    @staticmethod
    async def get_current_price(
        jetton_address: str, order_type: str, amount: float
    ) -> float:
        url = "https://api.ston.fi/v1/swap/simulate"
        headers = {"Accept": "application/json"}

        if order_type == OrderType.BUY.value:
            # Продаём TON, покупаем Jetton
            offer_address = PTONAddresses.MAINNET
            ask_address = jetton_address
        elif order_type == OrderType.SELL.value:
            # Продаём Jetton, покупаем TON
            offer_address = jetton_address
            ask_address = PTONAddresses.MAINNET
        else:
            raise ValueError(f"Неизвестный тип ордера: {order_type}")

        params = {
            "offer_address": offer_address,
            "ask_address": ask_address,
            "units": to_nano(amount),
            "slippage_tolerance": 1,
            "dex_v2": "true",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, params=params, headers=headers)
            if response.status_code == 200:
                content = response.json()
                swap_rate_str = content.get("swap_rate")
                return (
                    1 / float(swap_rate_str)
                    if order_type == OrderType.BUY.value
                    else float(swap_rate_str)
                )
            else:
                error_text = response.text
                raise Exception(
                    f"Не удалось получить swap_rate: {response.status_code}: {error_text}"
                )
