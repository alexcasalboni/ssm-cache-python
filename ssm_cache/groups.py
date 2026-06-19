from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from ssm_cache.exceptions import (
    InvalidParameterError,
    InvalidPathError,
)
from ssm_cache.parameters import (
    SecretsManagerParameter,
    SSMParameter,
)
from ssm_cache.refreshable import Refreshable


class SSMParameterGroup(Refreshable):
    """Concrete class that wraps multiple SSM Parameters."""

    def __init__(
        self,
        max_age: int | None = None,
        with_decryption: bool = True,
        base_path: str = "",
    ) -> None:
        super().__init__(max_age)

        self._with_decryption = with_decryption
        self._parameters: dict[str, SSMParameter] = {}
        self._base_path = base_path or ""

        self._validate_path(base_path)

    @staticmethod
    def _validate_path(path: str) -> None:
        if path and not path.startswith("/"):
            raise InvalidPathError(f"Invalid path: {path} (should start with a slash)")

    def parameter(self, path: str, add_prefix: bool = True) -> SSMParameter:
        if path in self._parameters:
            return self._parameters[path]

        if self._base_path and add_prefix:
            self._validate_path(path)
            path = f"{self._base_path}{path}"

        parameter = SSMParameter(path)
        parameter._group = self

        self._parameters[path] = parameter

        return parameter

    def parameters(
        self,
        path: str,
        recursive: bool = True,
        filters: Sequence[Any] | None = None,
    ) -> list[SSMParameter]:
        self._validate_path(path)

        if self._base_path:
            path = f"{self._base_path}{path}"

        items = self._get_parameters_by_path(
            with_decryption=self._with_decryption,
            path=path,
            recursive=recursive,
            filters=filters,
        )

        self._update_refresh_time(keep_oldest_value=True)

        parameters = []

        for name, item in items.items():
            parameter = self.parameter(name, add_prefix=False)
            parameter.load(
                value=item["Value"],
                version=item["Version"],
            )
            parameters.append(parameter)

        return parameters

    def secret(self, name: str) -> SecretsManagerParameter:
        if name in self._parameters:
            return self._parameters[name]  # type: ignore[return-value]

        parameter = SecretsManagerParameter(name)
        parameter._group = self

        self._parameters[name] = parameter

        return parameter

    def _refresh(self) -> None:
        names = [param.full_name for param in self.get_loaded_parameters()]

        items, invalid_names = self._get_parameters(
            names,
            self._with_decryption,
        )

        if invalid_names:
            raise InvalidParameterError(",".join(invalid_names))

        for parameter in self.get_loaded_parameters():
            if parameter.name not in items:
                raise InvalidParameterError(parameter.name)

            parameter.load(
                value=items[parameter.name]["Value"],
                version=items[parameter.name]["Version"],
            )

    def get_loaded_parameters(self) -> Iterable[SSMParameter]:
        return self._parameters.values()

    def __len__(self) -> int:
        return len(self._parameters)
