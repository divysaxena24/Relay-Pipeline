
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ModelProvider(Protocol):

    def generate(
        self,
        question: str,
        context: str = ""
    ) -> dict[str, Any]:
        ...

    def check_evidence(
        self,
        question: str,
        context: str
    ) -> dict[str, Any]:
        ...
