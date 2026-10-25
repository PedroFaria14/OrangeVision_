class ApplicationError(Exception):
    """Falha controlada traduzida pelo adaptador HTTP, sem dependência do framework."""

    def __init__(
        self,
        status_code: int,
        detail: str | list[dict[str, str]],
        headers: dict[str, str] | None = None,
    ):
        super().__init__('application_operation_failed')
        self.status_code = status_code
        self.detail = detail
        self.headers = headers
