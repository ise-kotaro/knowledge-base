"""Entra ID（Microsoft ID プラットフォーム）の OpenID Connect discovery 文書と署名鍵を表示する。

資格情報は不要。公開エンドポイントにGETするだけで、Issuerやトークン署名鍵（JWKS）を確認できる。
"""
import json
import urllib.request

TENANT = "common"  # 自テナントのIDに置き換えれば、そのテナント固有のissuer等が取れる
DISCOVERY_URL = (
    f"https://login.microsoftonline.com/{TENANT}/v2.0/.well-known/openid-configuration"
)


def get_json(url):
    with urllib.request.urlopen(url, timeout=10) as res:
        return json.load(res)


def main():
    discovery = get_json(DISCOVERY_URL)
    for key in ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri"):
        print(f"{key}: {discovery[key]}")

    jwks = get_json(discovery["jwks_uri"])
    print(f"署名鍵の数: {len(jwks['keys'])}")
    first = jwks["keys"][0]
    print(f"先頭の鍵: kid={first['kid']}, alg={first.get('alg')}, use={first.get('use')}")


if __name__ == "__main__":
    main()
