"""Application-specific exceptions."""


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, code: str = "app_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Recurso no encontrado") -> None:
        super().__init__(message=message, code="not_found")


class ValidationBusinessError(AppError):
    """Raised when a business validation fails."""

    def __init__(self, message: str, code: str = "validation_error") -> None:
        super().__init__(message=message, code=code)


class ConfigurationError(AppError):
    """Raised when required configuration is missing or invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="configuration_error")


class InvalidSmmlvError(ConfigurationError):
    """Raised when SMMLV is not configured for salary category calculations."""

    def __init__(self) -> None:
        super().__init__(
            "SMMLV no está configurado o es inválido. "
            "Configure un valor mayor que cero antes de calcular categorías salariales."
        )


class RealtimeServiceError(AppError):
    """Raised when the realtime voice provider cannot fulfill a request."""

    def __init__(
        self,
        message: str = "No fue posible iniciar la conversación de voz.",
        code: str = "realtime_service_unavailable",
    ) -> None:
        super().__init__(message=message, code=code)
