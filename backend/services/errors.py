"""Domain errors. The API layer maps these to HTTP status codes."""


class ModelLedgerError(Exception):
    pass


class NotFoundError(ModelLedgerError):
    pass


class DuplicateError(ModelLedgerError):
    def __init__(self, message: str, existing_id: str | None = None):
        super().__init__(message)
        self.existing_id = existing_id


class ValidationFailure(ModelLedgerError):
    pass
