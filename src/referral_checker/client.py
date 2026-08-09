"""GraphQL transport adapter."""

import time
from collections.abc import Awaitable, Callable, Mapping
from contextlib import AsyncExitStack
from importlib.resources import files
from types import TracebackType
from typing import Any, Final, Self, cast

import orjson
from aiolimiter import AsyncLimiter
from gql import Client, GraphQLRequest, gql
from gql.client import AsyncClientSession
from gql.transport.exceptions import (
    TransportError,
    TransportQueryError,
    TransportServerError,
)
from gql.transport.httpx import HTTPXAsyncTransport
from loguru import logger
from tenacity import AsyncRetrying, RetryCallState, retry_if_exception_type
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_exponential_jitter

from referral_checker.exceptions import AuthenticationError
from referral_checker.models import ReferralResult, Status
from referral_checker.settings import Settings

type Executor = Callable[[GraphQLRequest], Awaitable[Mapping[str, Any]]]

_QUERY: Final = gql(
    files("referral_checker.graphql")
    .joinpath("validate_referral_code.graphql")
    .read_text(encoding="utf-8")
)
_AUTHENTICATION_CODES: Final = frozenset(
    {"AUTHENTICATION_ERROR", "FORBIDDEN", "UNAUTHENTICATED", "UNAUTHORIZED"}
)


def _json_dumps(value: Any) -> str:
    return orjson.dumps(value).decode()


def _before_sleep(state: RetryCallState) -> None:
    logger.warning(
        "retrying after attempt {}: {}",
        state.attempt_number,
        state.outcome.exception() if state.outcome else "unknown error",
    )


def _is_authentication_error(error: TransportError) -> bool:
    """Return whether a transport error means the session is no longer authorized."""
    if isinstance(error, TransportServerError):
        return error.code in (401, 403)
    if not isinstance(error, TransportQueryError):
        return False
    extensions = (
        error.extensions,
        *(
            item.get("extensions")
            for item in error.errors or []
            if isinstance(item, Mapping)
        ),
    )
    return any(
        isinstance(value, Mapping)
        and str(value.get("code", "")).upper() in _AUTHENTICATION_CODES
        for value in extensions
    )


class GraphQLReferralValidator:
    """Validate referral codes through the Zeabur GraphQL endpoint."""

    def __init__(self, settings: Settings, executor: Executor | None = None) -> None:
        self.settings = settings
        self._executor = executor
        origin = str(settings.origin).rstrip("/")
        headers = {
            "Origin": origin,
            "Referer": f"{origin}/",
            "X-Zeabur-Locale": settings.locale,
        }
        if settings.cookie is not None:
            headers["Cookie"] = settings.cookie.get_secret_value()
        transport = HTTPXAsyncTransport(
            url=str(settings.endpoint),
            headers=headers,
            timeout=settings.timeout_seconds,
            json_serialize=_json_dumps,
            json_deserialize=orjson.loads,
        )
        self._client = Client(
            transport=transport,
            execute_timeout=settings.timeout_seconds,
            fetch_schema_from_transport=False,
        )
        self._session: AsyncClientSession | None = None
        self._stack = AsyncExitStack()
        self._limiter = AsyncLimiter(settings.requests_per_second, 1)

    async def __aenter__(self) -> Self:
        """Open the shared GraphQL session."""
        if self._executor is None:
            self._session = await self._stack.enter_async_context(self._client)
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        """Close the shared GraphQL session."""
        if self._executor is None:
            await self._stack.aclose()
            self._session = None

    async def validate(self, code: str) -> ReferralResult:
        """Validate one referral code."""
        started = time.perf_counter()
        attempts = 0
        payload: Mapping[str, Any] | None = None
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.settings.retries),
                wait=wait_exponential_jitter(initial=0.25, max=4),
                retry=retry_if_exception_type((TransportError, TimeoutError)),
                before_sleep=_before_sleep,
                reraise=True,
            ):
                with attempt:
                    attempts = attempt.retry_state.attempt_number
                    payload = await self._execute(code)
            if payload is None:
                raise RuntimeError("retry loop completed without a response")
            result = cast(Mapping[str, Any], payload["validateReferralCode"])
            valid = bool(result["valid"])
            return ReferralResult(
                code=code,
                status=Status.VALID if valid else Status.INVALID,
                discount_percent=result.get("discountPercent"),
                reason=str(result.get("reason") or ""),
                latency_ms=(time.perf_counter() - started) * 1000,
                attempts=attempts,
            )
        except (TransportError, TimeoutError, KeyError, TypeError, ValueError) as error:
            logger.opt(exception=error).error("referral-code validation failed")
            return ReferralResult(
                code=code,
                status=Status.ERROR,
                reason=f"{type(error).__name__}: {error}",
                latency_ms=(time.perf_counter() - started) * 1000,
                attempts=max(attempts, 1),
            )

    async def _execute(self, code: str) -> Mapping[str, Any]:
        request = GraphQLRequest(
            _QUERY,
            variable_values={
                "code": code,
                "orderType": self.settings.order_type,
            },
            operation_name="ValidateReferralCode",
        )
        async with self._limiter:
            try:
                if self._executor is not None:
                    return await self._executor(request)
                if self._session is None:
                    raise RuntimeError(
                        "validator must be used as an async context manager"
                    )
                response = await self._session.execute(request)
            except TransportError as error:
                if _is_authentication_error(error):
                    raise AuthenticationError(
                        "Authentication failed; refresh REFCHECK_COOKIE and try again."
                    ) from error
                raise
        return response
