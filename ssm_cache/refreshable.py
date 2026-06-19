from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, ClassVar

import botocore.exceptions

from ssm_cache.filters import SSMFilter
from ssm_cache.utils import batch, utcnow


class Refreshable:
    """Abstract class for refreshable objects (with max-age)."""

    _ssm_client: ClassVar[Any] = None

    @classmethod
    def set_ssm_client(cls, client: Any) -> None:
        required_methods = ("get_parameters", "get_parameters_by_path")

        for method in required_methods:
            if not hasattr(client, method):
                raise TypeError(f"client must have a {method} method")

        cls._ssm_client = client

    @classmethod
    def _get_ssm_client(cls) -> Any:
        if cls._ssm_client is None:
            import boto3

            cls._ssm_client = boto3.client("ssm")

        return cls._ssm_client

    def __init__(self, max_age: int | None) -> None:
        self._last_refresh_time: datetime | None = None
        self._max_age = max_age
        self._max_age_delta = timedelta(seconds=max_age or 0)

    def _refresh(self) -> None:
        raise NotImplementedError

    def _should_refresh(self) -> bool:
        if not self._max_age:
            return False

        if not self._last_refresh_time:
            return True

        return utcnow() > self._last_refresh_time + self._max_age_delta

    def _update_refresh_time(self, keep_oldest_value: bool = False) -> None:
        now = utcnow()

        if keep_oldest_value and self._last_refresh_time:
            self._last_refresh_time = min(now, self._last_refresh_time)
        else:
            self._last_refresh_time = now

    def refresh(self) -> None:
        self._refresh()
        self._update_refresh_time()

    @staticmethod
    def _parse_value(param_value: str, param_type: str) -> str | list[str]:
        if param_type == "StringList":
            return param_value.split(",")

        return param_value

    @classmethod
    def _get_parameters(
        cls,
        names: Sequence[str],
        with_decryption: bool,
    ) -> tuple[dict[str, dict[str, Any]], list[str]]:
        items: dict[str, dict[str, Any]] = {}
        invalid_names: list[str] = []

        for name_batch in batch(names, 10):
            try:
                response = cls._get_ssm_client().get_parameters(
                    Names=list(name_batch),
                    WithDecryption=with_decryption,
                )
            except botocore.exceptions.ClientError as exc:
                # SSM raises ParameterNotFound (rather than listing names in
                # InvalidParameters) when a Secrets Manager reference doesn't
                # exist.  Normalise to the same invalid-name path so callers
                # always get InvalidParameterError.
                code = exc.response.get("Error", {}).get("Code", "")
                if code == "ParameterNotFound":
                    invalid_names.extend(list(name_batch))
                    continue
                raise

            invalid_names.extend(response["InvalidParameters"])

            for item in response["Parameters"]:
                item["Value"] = cls._parse_value(item["Value"], item["Type"])
                items[item["Name"]] = item

        return items, invalid_names

    @classmethod
    def _get_parameters_by_path(
        cls,
        with_decryption: bool,
        path: str,
        recursive: bool = True,
        filters: Sequence[Any] | None = None,
    ) -> dict[str, dict[str, Any]]:
        items: dict[str, dict[str, Any]] = {}

        client = cls._get_ssm_client()
        has_builtin_paginator = hasattr(client, "get_paginator")

        def serialize_filter(filter_obj: Any) -> Any:
            if isinstance(filter_obj, SSMFilter):
                return filter_obj.to_dict()

            return filter_obj

        if has_builtin_paginator:
            pages = client.get_paginator("get_parameters_by_path").paginate(
                Path=path,
                Recursive=recursive,
                WithDecryption=with_decryption,
                ParameterFilters=[serialize_filter(filter_obj) for filter_obj in (filters or [])],
            )
        else:
            pages = [
                client.get_parameters_by_path(
                    Path=path,
                    Recursive=recursive,
                    WithDecryption=with_decryption,
                    ParameterFilters=[
                        serialize_filter(filter_obj) for filter_obj in (filters or [])
                    ],
                )
            ]

        for page in pages:
            for item in page["Parameters"]:
                item["Value"] = cls._parse_value(item["Value"], item["Type"])
                items[item["Name"]] = item

        return items

    def refresh_on_error(
        self,
        error_class: type[BaseException] = Exception,
        error_callback: Callable[[], Any] | None = None,
        retry_argument: str | None = "is_retry",
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        if error_callback and not callable(error_callback):
            raise TypeError("error_callback must be callable")

        def true_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except error_class:
                    self.refresh()

                    if error_callback:
                        error_callback()

                    if retry_argument:
                        kwargs[retry_argument] = True

                    return func(*args, **kwargs)

            return wrapped

        return true_decorator
