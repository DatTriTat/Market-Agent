from dataclasses import dataclass


@dataclass
class AppError(Exception):
    status_code: int
    detail: str


class UpstreamError(AppError):
    def __init__(self, detail: str = "Upstream service error"):
        super().__init__(status_code=502, detail=detail)
