# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "fastapi",
#   "pyjwt",
#   "cryptography",
#   "httpx",
# ]
# ///
"""本物の Entra ID なしで、トークン検証の全経路（署名・iss・aud・期限・ロール）を動作確認する。

ローカルで生成した RSA 鍵ペアを「ローカルの IdP」に見立てる。
アプリ側はその公開鍵から鍵を引く検証器に差し替えて、HTTP 経路ごと TestClient で叩く。
署名の仕組み（RS256 + JWKS + kid 照合）は本番と同じものが動く。

実行: uv run demo_test.py （依存は先頭の PEP 723 メタデータから uv が自動解決する）
"""

import json
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

import main
from auth import TokenVerifier

ISSUER = "https://login.microsoftonline.com/00000000-0000-0000-0000-000000000000/v2.0"
AUDIENCE = "11111111-1111-1111-1111-111111111111"

# --- ローカルの IdP 役 -------------------------------------------------------
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
public_jwk["kid"] = "local-test-key"


def mint(**overrides) -> str:
    """ローカル IdP がトークンを発行する想定。有効なクレーム一式を既定値にする。"""
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-123",
        "iat": now,
        "exp": now + 3600,
        "scp": "User.Read",
        "roles": [],
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "local-test-key"})


# --- アプリ側にローカル鍵の検証器を差し込む ---------------------------------
main.verifier = TokenVerifier(
    issuer=ISSUER,
    audience=AUDIENCE,
    key_resolver=lambda token: jwt.PyJWK(public_jwk).key,
)
client = TestClient(main.app)

# --- テスト ------------------------------------------------------------------
failures = []


def check(name, actual, expected):
    ok = actual == expected
    print(f"{'PASS' if ok else 'FAIL'}: {name} (expected={expected}, actual={actual})")
    if not ok:
        failures.append(name)


check("認証不要の /public はトークンなしで200", client.get("/public").status_code, 200)
check("/me はトークンなしで401", client.get("/me").status_code, 401)

valid = mint()
res = client.get("/me", headers={"Authorization": f"Bearer {valid}"})
check("/me は正しいトークンで200", res.status_code, 200)
check("/me の応答に sub が入る", res.json().get("subject", ""), "user-123")

expired = mint(exp=int(time.time()) - 10)
check("期限切れトークンは401", client.get("/me", headers={"Authorization": f"Bearer {expired}"}).status_code, 401)

wrong_aud = mint(aud="99999999-9999-9999-9999-999999999999")
check("aud不一致は401", client.get("/me", headers={"Authorization": f"Bearer {wrong_aud}"}).status_code, 401)

wrong_iss = mint(iss="https://evil.example.com/v2.0")
check("iss不一致（なりすまし）は401", client.get("/me", headers={"Authorization": f"Bearer {wrong_iss}"}).status_code, 401)

check("/admin はロールなしで403", client.get("/admin", headers={"Authorization": f"Bearer {valid}"}).status_code, 403)
admin_token = mint(roles=["Admin"])
check("/admin は Adminロール付きで200", client.get("/admin", headers={"Authorization": f"Bearer {admin_token}"}).status_code, 200)

print()
if failures:
    raise SystemExit(f"{len(failures)} 件の失敗: {failures}")
print("全8ケース成功")
