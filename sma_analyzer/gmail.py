"""Gmail send-only HTTP transport. No network or authorization on import."""
import base64
from email.message import EmailMessage
import json
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .notifications import validate_email

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


class GmailError(RuntimeError):
    """Safe, user-facing error; never include bearer tokens or server responses."""


class GmailSender:
    """Short-lived bearer token in memory only; Google Play services owns consent.

    The native Android authorization request selects the configured sender's
    account. Re-authorize before each explicit send operation to obtain a fresh
    access token; no app-owned refresh token or client secret is needed.
    """
    def __init__(self, sender, transport=None, clock=None):
        self.sender = validate_email(sender)
        if not self.sender:
            raise ValueError("Configure a Gmail sender address in settings.py.")
        self._transport = transport or urlopen
        self._clock = clock or time.monotonic
        self._token = None
        self._expires_at = 0

    @property
    def connected(self):
        return bool(self._token and self._clock() < self._expires_at)

    def accept_access_token(self, token):
        if not isinstance(token, str) or not token.strip():
            raise GmailError("Google did not grant send access. Connect Gmail again.")
        self._token = token
        # Google access tokens normally last an hour; use a conservative cache.
        self._expires_at = self._clock() + 45*60

    def disconnect(self):
        self._token = None
        self._expires_at = 0

    def send(self, alert, recipient):
        recipient = validate_email(recipient)
        if not recipient:
            raise GmailError("Save a recipient email address in Settings first.")
        if not self.connected:
            raise GmailError("Connect Gmail to authorize sending, then try again.")
        message = EmailMessage()
        message["From"], message["To"] = self.sender, recipient
        message["Subject"] = alert.subject
        message.set_content(alert.body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        request = Request(GMAIL_SEND_URL, data=json.dumps({"raw": raw}).encode(), method="POST",
                          headers={"Authorization": f"Bearer {self._token}",
                                   "Content-Type": "application/json"})
        # Android OpenSSL does not reliably locate the system CA store.
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
        try:
            with self._transport(request, timeout=15, context=context) as response:
                result = json.loads(response.read().decode("utf-8"))
            if not isinstance(result, dict) or not result.get("id"):
                raise GmailError("Gmail returned no message confirmation. Check Sent before retrying.")
            return result["id"]
        except HTTPError as error:
            if error.code == 401:
                self.disconnect()
                raise GmailError("Gmail authorization expired. Connect Gmail again.") from None
            if error.code == 403:
                raise GmailError("Gmail refused sending. Check Gmail API, OAuth setup and send permission.") from None
            if error.code == 429:
                raise GmailError("Gmail sending limit reached. Try again later.") from None
            raise GmailError("Gmail rejected the message. Check Sent before retrying.") from None
        except (URLError, OSError, ValueError):
            raise GmailError("Could not confirm Gmail delivery. Check your connection and Sent before retrying.") from None
