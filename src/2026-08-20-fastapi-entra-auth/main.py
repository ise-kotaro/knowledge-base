"""Entra ID のアクセストークンで保護された FastAPI アプリの実装例。"""

import os

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth import TokenVerifier

TENANT_ID = os.environ.get("ENTRA_TENANT_ID", "<テナントID>")
CLIENT_ID = os.environ.get("ENTRA_CLIENT_ID", "<アプリのクライアントID>")

# 本番の検証器。JWKS はさっきのノートの discovery 文書が指す URL と同じもの
verifier = TokenVerifier(
    issuer=f"https://login.microsoftonline.com/{TENANT_ID}/v2.0",
    audience=CLIENT_ID,
    jwks_uri=f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys",
)

bearer = HTTPBearer(auto_error=False)
app = FastAPI()


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    """Authorization: Bearer ヘッダのトークンを検証し、クレームを返す。"""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="トークンがありません")
    try:
        return verifier.verify(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="トークンが不正または失効しています"
        )


@app.get("/public")
def public():
    return {"message": "認証なしで見られるエンドポイント"}


@app.get("/me")
def me(user: dict = Depends(current_user)):
    return {"subject": user["sub"], "scopes": user.get("scp"), "roles": user.get("roles", [])}


@app.get("/admin")
def admin(user: dict = Depends(current_user)):
    if "Admin" not in user.get("roles", []):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Adminロールが必要です")
    return {"message": "管理者向けエンドポイント"}
