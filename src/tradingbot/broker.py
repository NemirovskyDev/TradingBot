"""Interface da corretora. Na fase 1 não existe implementação real: nenhuma ordem pode ser enviada.
A fase 2 acrescenta uma implementação paper da Alpaca sem mexer no resto do código."""
from typing import Protocol

from tradingbot.risk import Order, Position


class Broker(Protocol):
    def submit_order(self, order: Order) -> str: ...

    def get_positions(self) -> list[Position]: ...


class NullBroker:
    def submit_order(self, order: Order) -> str:
        raise NotImplementedError("Fase 2: ordens ainda não implementadas")

    def get_positions(self) -> list[Position]:
        raise NotImplementedError("Fase 2: ordens ainda não implementadas")
