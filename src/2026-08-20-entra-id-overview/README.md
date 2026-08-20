---
title: Entra ID とは
date: 2026-08-20
updated: 2026-08-20
tags: [microsoft, entra-id, identity, idp, oauth, oidc]
related: [src/2026-08-20-fastapi-entra-auth/]
---

# Entra ID とは

## 概要

**Microsoft Entra ID** は、Microsoft が提供するクラウドベースの ID およびアクセス管理サービスである。
ユーザー、デバイス、アプリ、リソースに対する認証、アクセスポリシーの適用、保護を担う。
旧称は **Azure Active Directory（Azure AD）** で、2023年に名称だけが変更されている。[^rename]
Microsoft 365 や Azure のサブスクライバーであれば既に利用者であり、これらのテナントは自動的に Microsoft Entra テナントになっている。

[^rename]: 改称は2023年7月11日に公表され、名前の書き換えは同年8月15日から始まった。サービスプランの表示名は同年10月1日に変更された。略号はスペース上どうしても必要な場合に限り ME-ID を使う。

## できること

「Entra ID」が直接担うのは、**認証**（サインインしているのが本人かの検証）と**認可**（何へのアクセスを許すかの判定）である。

- シングルサインオン（SSO）で、統合した複数のアプリへのサインインを一元化する。
- 多要素認証（MFA）で、パスワード以外の要素を追加する。
- 条件付きアクセスで、場所・デバイス・リスクなどの条件に応じたポリシーを適用する。
- オンプレミスの Active Directory と Microsoft Entra Connect で同期し、ハイブリッド構成を組む。

## 「Azure AD」との関係

名称変更はブランドの整理であり、機能の変更を伴わない。
ログイン URL、API、MSAL（Microsoft Authentication Library）、PowerShell の既存コマンドレットはそのまま動き、価格も変わっていない。
Windows Server の Active Directory は対象外で、名称は変わっていない点に注意が必要である。
改称の動機の一つが、このオンプレミス製品との混同を避けることだったと Microsoft は説明している。
例外として、Azure AD B2C だけは名称が変わっていない（新規顧客向けの販売は2025年5月1日に終了している）。

## 製品ファミリの中での位置づけ

「Microsoft Entra」は ID とネットワークアクセスの製品ファミリ名で、「Entra ID」はその中の基本製品にあたる。
ファミリの主な製品は次のとおりである。

| 製品 | 役割 |
|---|---|
| Microsoft Entra ID | ファミリの中核。クラウド型の ID およびアクセス管理 |
| Microsoft Entra 外部 ID | 顧客・パートナー向けの ID 管理（B2B / CIAM） |
| Microsoft Entra Domain Services | Kerberos / LDAP が必要なレガシーアプリ向けのマネージドドメイン |
| Microsoft Entra ワークロード ID | アプリやサービスなど、人間以外のワークロードの ID 管理 |
| Microsoft Entra Internet / Private Access | ネットワークアクセスの保護（SSE 領域） |

## 開発者が直接触れる部分

開発の現場で直接相手をするのは **Microsoft ID プラットフォーム** である。
OAuth 2.0 / OpenID Connect（OIDC）準拠のエンドポイント群が `login.microsoftonline.com` 配下に公開されており、改称後もこの URL は変わっていない。
各テナントのエンドポイント構成や署名鍵は、資格情報なしで取れる公開の discovery 文書（`/.well-known/openid-configuration`）から辿れる。

## JWKS とは

**JWKS（JSON Web Key Set）** は、JWT（JSON Web Token）の署名を検証できる公開鍵をまとめた JSON 文書である。
この文書の場所は discovery 文書の `jwks_uri` が指しており、その中身が署名の検証に使う鍵だと OIDC の仕様で定められている。[^jwks-uri]

[^jwks-uri]: OpenID Connect Discovery 1.0 の3章で、「jwks_uri は、OP からの署名を RP が検証するために使う署名鍵を含む JWK Set 文書の URL」と定義されている。

JWT はヘッダー、ペイロード、署名の3部からなる。
ヘッダーには、署名に使った鍵を示す ID（kid）とアルゴリズム（alg）が入っている。
トークンを受け取った側は、JWKS の中から「kid」が一致する鍵を取り出して署名を検証する。
この照合によって、トークンが正規の発行者から来ていて、改ざんされていないことを確認できる。

各鍵が持つ主なフィールドは次のとおりである。

| フィールド | 意味 |
|---|---|
| kid | 鍵の ID。JWT ヘッダーの kid と照合する |
| kty | 鍵の種類。Entra ID では RSA |
| n, e | RSA 公開鍵の本体（モジュラスと指数） |
| use | 用途。sig は署名用を示す |
| x5c | 対応する X.509 証明書 |

先の実行結果に鍵が9個も並んでいたのは、**鍵ローテーション**のためである。
署名鍵は定期的に付け替えられ、切替期間には新旧の鍵が JWKS に並存する。
検証側は「kid」で鍵を選ぶので、ローテーションの最中でも検証を継続できる。

## 「.well-known」の由来

discovery 文書のパスに現れる `.well-known` は、OpenID の造語ではなく、**well-known URI** と呼ばれる共通の仕組みに由来する。[^well-known]
サイト全体に関わる定型的な情報の置き場所を `/.well-known/` に固定することで、クライアントはホスト名さえ分かれば、個別の設定なしで設定情報に辿り着けるという発想である。
OIDC では `openid-configuration` というサフィックスがこの仕組みに登録されており、準拠する IdP はみな同じ場所に discovery 文書を公開する。

[^well-known]: well-known URI は RFC 5785（2010年）で導入され、RFC 8615（2019年）に更新された。登録済みのサフィックスは IANA のレジストリで管理されている。

先頭にドットが付く理由は、RFC 8615 の FAQ に率直に書かれている。
短くて意味が通じ、当時の検索インデックスの調査でも実際には使われていなかったからだという。
ドットで始まるパス名は、一般のサイトがコンテンツ用に使うことがほぼないので、既存の URL と衝突する危険が小さい。

## ライセンス

ライセンスは Free、P1、P2 の各プランと、ファミリ製品をまとめたスイートに分かれる。
Microsoft 365 のライセンスにも含まれており、E3 には P1、E5 には P2 が同梱される。
どの機能がどのプランで有効になるかの詳細比較は、本ノートでは確認していない。[^license]

[^license]: 現行プランの機能対応は Microsoft の価格ページで確認するのが確実である。 https://www.microsoft.com/security/business/microsoft-entra-pricing

## サンプルコード

完全版は同じディレクトリの `get_discovery.py` で、実行確認済みである。
OIDC の discovery 文書と署名鍵（JWKS）を、標準ライブラリだけで取得する。

```python
def main():
    discovery = get_json(DISCOVERY_URL)
    for key in ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri"):
        print(f"{key}: {discovery[key]}")

    jwks = get_json(discovery["jwks_uri"])
    print(f"署名鍵の数: {len(jwks['keys'])}")
```

実行方法と実行結果は次のとおりである。

```console
$ python3 get_discovery.py
issuer: https://login.microsoftonline.com/{tenantid}/v2.0
authorization_endpoint: https://login.microsoftonline.com/common/oauth2/v2.0/authorize
token_endpoint: https://login.microsoftonline.com/common/oauth2/v2.0/token
jwks_uri: https://login.microsoftonline.com/common/discovery/v2.0/keys
署名鍵の数: 9
先頭の鍵: kid=AahUf1bCXvx0JTRcXLrr0U4SluY, alg=None, use=sig
```

## 出典

- [Microsoft Entraとは - Microsoft Learn](https://learn.microsoft.com/ja-jp/entra/fundamentals/what-is-entra)
- [Azure Active Directory の新しい名称 - Microsoft Learn](https://learn.microsoft.com/ja-jp/entra/fundamentals/new-name)
- [OpenID Connect Discovery 1.0](https://openid.net/specs/openid-connect-discovery-1_0.html)
- [RFC 8615: Well-Known Uniform Resource Identifiers (URIs)](https://www.rfc-editor.org/rfc/rfc8615)

## 関連ノート

- [FastAPI で Entra ID 認証付き API を実装する](../2026-08-20-fastapi-entra-auth/README.md)
