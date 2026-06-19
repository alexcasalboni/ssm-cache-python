from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class SSMFilter:
    KEY_NAME = "Name"
    KEY_TYPE = "Type"
    KEY_KEYID = "KeyId"
    KEY_PATH = "Path"
    KEY_ALLOWED_VALUES = (
        KEY_NAME,
        KEY_TYPE,
        KEY_KEYID,
        KEY_PATH,
    )

    OPTION_EQUALS = "Equals"
    OPTION_BEGINSWITH = "BeginsWith"
    OPTION_RECURSIVE = "Recursive"
    OPTION_ONELEVEL = "OneLevel"
    OPTION_ALLOWED_VALUES = (OPTION_EQUALS, OPTION_BEGINSWITH)
    OPTION_PATH_ALLOWED_VALUES = (OPTION_RECURSIVE, OPTION_ONELEVEL)

    def __init__(self, key: str, option: str = OPTION_EQUALS) -> None:
        self._validate_config(key, option)
        self._key = key
        self._option = option
        self._values: set[str] = set()

    @classmethod
    def _validate_config(cls, key: str, option: str) -> None:
        if key not in cls.KEY_ALLOWED_VALUES:
            raise ValueError(f"Invalid key value: {key}")
        if key != cls.KEY_PATH and option not in cls.OPTION_ALLOWED_VALUES:
            raise ValueError(f"Invalid option value: {option}")
        if key == cls.KEY_PATH and option not in cls.OPTION_PATH_ALLOWED_VALUES:
            raise ValueError(f"Invalid option value for Path key: {option}")

    def value(self, value: str) -> SSMFilter:
        if len(self._values) == 50:
            raise ValueError("You can't set more than 50 values for each filter.")
        self._values.add(value)
        return self  # chainable

    def values(self, values: Iterable[str]) -> SSMFilter:
        for value in values:
            self.value(value)
        return self  # chainable

    def to_dict(self) -> dict[str, Any]:
        filter_dict: dict[str, Any] = {
            "Key": self._key,
            "Option": self._option,
        }
        if self._values:
            filter_dict["Values"] = list(self._values)
        return filter_dict


class SSMFilterName(SSMFilter):
    def __init__(self, option: str = SSMFilter.OPTION_EQUALS) -> None:
        super().__init__(self.KEY_NAME, option)
        raise NotImplementedError("Not implemented yet (by AWS)")


class SSMFilterType(SSMFilter):
    TYPE_STRING = "String"
    TYPE_STRINGLIST = "StringList"
    TYPE_SECURESTRING = "SecureString"
    TYPE_ALLOWED_VALUES = (TYPE_STRING, TYPE_STRINGLIST, TYPE_SECURESTRING)

    def __init__(self, option: str = SSMFilter.OPTION_EQUALS) -> None:
        super().__init__(self.KEY_TYPE, option)

    def value(self, value: str) -> SSMFilter:
        if value not in self.TYPE_ALLOWED_VALUES:
            raise ValueError(f"Invalid value for Type filter: {value}")
        return super().value(value)


class SSMFilterKeyId(SSMFilter):
    def __init__(self, option: str = SSMFilter.OPTION_EQUALS) -> None:
        super().__init__(self.KEY_KEYID, option)


class SSMFilterPath(SSMFilter):
    def __init__(self, option: str = SSMFilter.OPTION_RECURSIVE) -> None:
        super().__init__(self.KEY_PATH, option)
        raise NotImplementedError("Not implemented yet (by AWS)")
