"""Private HTTP adapter transport with server-bound identity."""
import json
import requests
from config import settings
from services.auth import current_claims, mint_internal_token
class ERPResponse:
    def __init__(self, status_code, body): self.status_code, self.text = status_code, body
    @property
    def ok(self): return 200 <= self.status_code < 300
    def json(self): return json.loads(self.text) if self.text else None
    def raise_for_status(self):
        if not self.ok: raise RuntimeError(f"ERP API returned {self.status_code}: {self.text}")
def is_configured(): return bool(settings.erpnext_url and settings.adapter_api_url)
def request(method, path, params=None, json_body=None, user_email=None, timeout=30):
    claims = current_claims.get()
    if not claims or (user_email and user_email != claims["email"]):
        raise PermissionError("ERP identity must match the authenticated execution context")
    if not path.startswith("/") or path.startswith("//") or ".." in path:
        raise ValueError("Invalid adapter path")
    response = requests.request(method.upper(), settings.adapter_api_url.rstrip("/") + path,
        params=params, json=json_body, timeout=timeout, allow_redirects=False,
        headers={"Authorization": "Bearer " + mint_internal_token(claims)})
    return ERPResponse(response.status_code, response.text)
