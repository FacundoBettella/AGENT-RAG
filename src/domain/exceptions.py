class ContentBlockedError(Exception):
    """Raised when moderation blocks a request before it reaches OpenAI."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
