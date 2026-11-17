from typing import Any


class AppException(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", code: str = "NOT_FOUND") -> None:
        super().__init__(404, code, message)


class ConflictError(AppException):
    def __init__(self, message: str = "Resource already exists", code: str = "CONFLICT") -> None:
        super().__init__(409, code, message)


class ValidationAppError(AppException):
    def __init__(self, message: str, code: str = "VALIDATION_ERROR", details: Any | None = None) -> None:
        super().__init__(422, code, message, details)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Not authenticated", code: str = "UNAUTHORIZED") -> None:
        super().__init__(401, code, message)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Access denied", code: str = "FORBIDDEN") -> None:
        super().__init__(403, code, message)
