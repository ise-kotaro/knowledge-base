"""Entra ID（OIDC 準拠の IdP）が発行したアクセストークンを検証する最小実装。"""

from collections.abc import Callable

import jwt
from jwt import PyJWKClient


class TokenVerifier:
    """JWKS から署名鍵を引き、JWT の署名・発行者・対象者・有効期限をまとめて検証する。"""

    def __init__(
        self,
        issuer: str,
        audience: str,
        *,
        jwks_uri: str | None = None,
        key_resolver: Callable[[str], object] | None = None,
    ):
        self.issuer = issuer
        self.audience = audience
        # PyJWKClient は JWKS の取得とキャッシュを担う（本番経路）
        self._jwk_client = PyJWKClient(jwks_uri) if jwks_uri else None
        # テスト経路: ローカルの鍵などから解決する関数を差し込める
        self._key_resolver = key_resolver

    def verify(self, token: str) -> dict:
        """検証済みクレームを返す。失敗時は jwt.PyJWTError の例外を送出する。"""
        return jwt.decode(
            token,
            self._resolve_key(token),
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
            options={"require": ["exp", "iat", "iss", "aud"]},
        )

    def _resolve_key(self, token: str):
        if self._key_resolver is not None:
            return self._key_resolver(token)
        return self._jwk_client.get_signing_key_from_jwt(token).key
