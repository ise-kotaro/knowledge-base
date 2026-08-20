---
title: FastAPI で Entra ID 認証付き API を実装する
date: 2026-08-20
updated: 2026-08-20
tags: [fastapi, python, entra-id, jwt, oauth, oidc]
related: [src/2026-08-20-entra-id-overview/]
---

# FastAPI で Entra ID 認証付き API を実装する

## 概要

Entra ID のような IdP に認証を委譲する構成では、API 側が担うのはアクセストークンの検証だけである。
本ノートは、FastAPI 製の API を Entra ID が発行する JWT で保護する最小実装と、その動作確認のやり方をまとめた補足ノートである。
Entra ID 自体の解説は「[Entra ID とは](../2026-08-20-entra-id-overview/README.md)」を参照。

## 構成要素と API 側の責務

認証を委譲する構成の登場人物は3つである。

| 役割 | 担当すること |
|---|---|
| IdP（認可サーバー） | ユーザーの認証とトークンの発行。Entra ID が担う |
| クライアント | 認可コードフロー＋PKCE でトークンを取得する。本ノートの扱い外 |
| リソースサーバー | トークンを検証して保護対象を返す。FastAPI アプリがこれ |

リソースサーバー側が実装すべき検証は、次の3点に集約される。

1. 署名の検証。JWKS から鍵を kid で引いて行う
2. `iss`（発行者）、`aud`（宛先が自分の API か）、`exp`（有効期限）の確認
3. `scp` や `roles` のクレームを見た認可の分岐[^claims]

[^claims]: 「scp」は委任された権限（scope）、「roles」はアプリケーションロールの列である。どちらも Entra 管理センターのアプリ登録で定義する。

## 認証はどこで起きるか

認証そのものは FastAPI 側では一切行われない。
本人確認（パスワードや多要素認証の入力）は Entra ID のログイン画面上で行われ、API に届くのは認証済みであることの証明としての JWT だけである。

流れの全体像は次のとおりである。

```
1. ユーザーがクライアントの「ログイン」を押す
2. クライアントはブラウザを Entra ID の認可エンドポイントにリダイレクトする
3. ユーザーは Entra ID の画面でサインインする          ← 認証はここ
4. Entra ID が認可コードをクライアントに返す
5. クライアントは認可コードと PKCE の verifier を token エンドポイントに送る
6. Entra ID がアクセストークン（JWT）を発行する
7. クライアントは JWT を Authorization: Bearer に付けて API を叩く
8. API は署名・iss・aud・exp を検証して受け入れる      ← 本ノートの実装範囲
```

この住み分けにより、API 側はパスワードを一切扱わなくて済む。
パスワードの保存やリセットは IdP の責務であり、これが認証を委譲する構成の利点である。

## 実装

検証の核心は `auth.py` の数行である。

```python
return jwt.decode(
    token,
    self._resolve_key(token),
    algorithms=["RS256"],
    audience=self.audience,
    issuer=self.issuer,
    options={"require": ["exp", "iat", "iss", "aud"]},
)
```

本番の鍵解決は、JWKS を取得してキャッシュする PyJWKClient が担う。
JWKS の URL はテナントの discovery 文書が指すものと同じで、テナント ID から機械的に組み立てられる。
一方、テストでは `key_resolver` に関数を差し込めるようにしてあり、ネットワークなしで検証経路を動かせる。

`main.py` 側は、FastAPI の依存注入で保護を書く。

- `current_user` が Bearer トークンを検証してクレームを返す。トークンなし・不正は 401
- `/admin` はクレームの `roles` に「Admin」が無ければ 403

## 動作確認

手元に Entra テナントがなくても全経路を確認できるよう、ローカルで生成した RSA 鍵ペアを IdP に見立てている。
署名の仕組み（RS256、公開鍵による検証、kid の付与）は本番と同じものが動く。

```bash
cd src/2026-08-20-fastapi-entra-auth
uv run demo_test.py   # 依存はスクリプト先頭の PEP 723 メタデータから uv が自動解決する
```

実行結果は次のとおりで、全8ケースが成功した。

```console
PASS: 認証不要の /public はトークンなしで200
PASS: /me はトークンなしで401
PASS: /me は正しいトークンで200
PASS: /me の応答に sub が入る
PASS: 期限切れトークンは401
PASS: aud不一致は401
PASS: iss不一致（なりすまし）は401
PASS: /admin はロールなしで403 / Adminロール付きで200
```

## 本番の Entra ID につなぐ

環境変数に `ENTRA_TENANT_ID` と `ENTRA_CLIENT_ID` を渡せば、検証器が本物のエンドポイントを指す。
実機での検証は未実施で、Entra テナントとアプリ登録が必要になる。

## 関連ノート

- [Entra ID とは](../2026-08-20-entra-id-overview/README.md)
