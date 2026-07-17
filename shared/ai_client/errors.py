from fastapi import status


class AiClientError(Exception):
    """Base for all ai_client failures.

    Callers should log at the call site (they have the conversation/tool
    context this module doesn't) — these classes intentionally carry no
    logging of their own.
    """

    def __init__(self, message: str, status_code: int = status.HTTP_502_BAD_GATEWAY):
        self.message = message
        self.status_code = status_code


class AiUnavailableError(AiClientError):
    def __init__(self, message: str = "AI provider is unavailable"):
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class AiRateLimitedError(AiClientError):
    def __init__(self, retry_after: int, message: str = "AI provider is rate limited"):
        super().__init__(message, status_code=status.HTTP_429_TOO_MANY_REQUESTS)
        self.retry_after = retry_after
