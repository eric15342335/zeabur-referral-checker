"""Application-specific exceptions."""


class AuthenticationError(RuntimeError):
    """The configured session cookie was rejected by the remote service."""
