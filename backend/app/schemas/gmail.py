from pydantic import BaseModel, Field


class GmailMessage(BaseModel):
    id: str
    thread_id: str
    subject: str
    sender: str
    sender_email: str | None = None
    recipient: str | None = None
    received_at: str | None = None
    snippet: str
    is_unread: bool = False
    labels: list[str] = Field(default_factory=list)


class GmailMessagesResponse(BaseModel):
    status: str = "ok"
    connected: bool = True
    total: int
    messages: list[GmailMessage]


class GoogleConnectionStatus(BaseModel):
    status: str = "ok"
    connected: bool
    email: str | None = None
    provider: str | None = None
    has_access_token: bool = False
    has_refresh_token: bool = False
    scopes: list[str] = Field(default_factory=list)
    login_url: str | None = None
    message: str | None = None
    mail_read_available: bool = False