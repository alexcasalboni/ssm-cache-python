from __future__ import annotations

from typing import TYPE_CHECKING

from ssm_cache.exceptions import (
    InvalidParameterError,
    InvalidVersionError,
)
from ssm_cache.refreshable import Refreshable

if TYPE_CHECKING:
    from ssm_cache.groups import SSMParameterGroup


class SSMParameter(Refreshable):
    """Concrete class for an individual SSM Parameter."""

    def __init__(
        self,
        param_name: str,
        max_age: int | None = None,
        with_decryption: bool = True,
    ) -> None:
        super().__init__(max_age)

        if not param_name:
            raise ValueError("Must specify name")

        (
            self._name,
            self._version,
            self._is_pinned_version,
        ) = self._parse_version(param_name)

        self._value: str | list[str] | None = None
        self._with_decryption = with_decryption
        self._group: SSMParameterGroup | None = None

    def load(self, value: str | list[str], version: int | None) -> None:
        """Load parameter values without direct protected mutation."""
        self._value = value
        self._version = version

    @staticmethod
    def _parse_version(param_name: str) -> tuple[str, int | None, bool]:
        name: str = param_name
        version: int | None = None
        is_pinned_version = False

        if ":" in param_name:
            name, version_str = param_name.split(":")

            if version_str.isdigit() and int(version_str) > 0:
                version = int(version_str)
                is_pinned_version = True
            else:
                raise InvalidVersionError(f"Invalid version: {version_str}")

        return name, version, is_pinned_version

    def _should_refresh(self) -> bool:
        if self._group:
            return self._group._should_refresh()

        return super()._should_refresh()

    def _refresh(self) -> None:
        if self._group:
            self._group.refresh()

        items, invalid_parameters = self._get_parameters(
            [self.full_name],
            self._with_decryption,
        )

        if invalid_parameters or self._name not in items:
            raise InvalidParameterError(f"{self._name} is invalid. {invalid_parameters} - {items}")

        self.load(
            value=items[self._name]["Value"],
            version=items[self._name]["Version"],
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def full_name(self) -> str:
        if self._version and self._is_pinned_version:
            return f"{self._name}:{self._version}"

        return self._name

    @property
    def version(self) -> int | None:
        if self._version is None or self._should_refresh():
            self.refresh()

        return self._version

    @property
    def value(self) -> str | list[str] | None:
        if self._value is None or self._should_refresh():
            self.refresh()

        return self._value


class SecretsManagerParameter(SSMParameter):
    PREFIX = "/aws/reference/secretsmanager/"

    def __init__(
        self,
        param_name: str,
        max_age: int | None = None,
        with_decryption: bool = True,
    ) -> None:
        param_name = self._add_prefix(param_name)
        super().__init__(param_name, max_age, with_decryption)

    @classmethod
    def _add_prefix(cls, param_name: str) -> str:
        if not param_name:
            raise ValueError("Secret name can't be empty")

        if not param_name.startswith(cls.PREFIX):
            if param_name.startswith("/"):
                raise InvalidParameterError(param_name)

            param_name = f"{cls.PREFIX}{param_name}"

        return param_name
