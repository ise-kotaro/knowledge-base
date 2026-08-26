---
title: REST API のファセットと HATEOAS
date: 2026-08-25
updated: 2026-08-25
tags: [rest, api-design, facets, faceted-search, hateoas, hypermedia]
related: [src/2026-08-24-software-taxonomy/]
---

# REST API のファセットと HATEOAS

## 概要

検索系の REST API で隣り合わせに出てくる2つの概念、ファセットと HATEOAS をまとめたノートである。
**ファセット**（facets）は、検索結果を属性ごとに集計し、絞り込み候補としてクライアントに返す仕組みを指す。[^facet-origin]
**HATEOAS**（Hypermedia as the Engine of Application State）は、REST の制約の1つで、レスポンスに埋め込まれたリンクをたどることでアプリケーションの状態を遷移させる設計原則である。
両者は別の話題であるが、ファセットの各候補をリンクとして返す設計で接点を持つ。

[^facet-origin]: facet の語源はフランス語の facette（小さな面）で、宝石の切子面を指す。ひとつのデータを属性という「面」から眺める、という発想で検索の用語に転用された。

## ファセットのやり取り

ファセットの典型例は、EC サイトの絞り込み欄に出る「ブランド: Nike (12)／Adidas (8)」のような候補と件数の一覧である。
この仕組みはファセット検索（faceted search）、またはファセットナビゲーションと呼ばれる。

基本的なやり取りは次の流れになる。

1. クライアントがキーワードで検索する
2. サーバーが結果一覧とファセットを同じレスポンスで返す
3. ユーザーがファセットの値を選ぶ
4. クライアントがその値を条件に加えて再検索する

最初のリクエストとレスポンスの例。

```http
GET /products?q=sneakers
```

```json
{
  "total": 125,
  "items": ["..."],
  "facets": [
    {
      "field": "brand",
      "values": [
        { "value": "Nike", "count": 12 },
        { "value": "Adidas", "count": 8 }
      ]
    }
  ]
}
```

ユーザーが Nike を選んだあとは、選択済みの値を通常のクエリパラメータで表す。

```http
GET /products?q=sneakers&brand=Nike
```

ファセットの役割はあくまで候補の提示であり、絞り込み条件そのものではない。
この区別を分けておくと、リクエストの意味をクエリパラメータだけで完結させられる。
なおファセットは REST の制約に含まれる概念ではなく、検索 API で広く使われるデザインパターンである。

## ファセット設計の論点

ファセットを実装するときに詰める必要がある点は主に3つある。

- **ファセット除外**（disjunctive faceting）：ブランドで Nike を選んだあとも、ブランド軸のファセットには他ブランドの件数を残したい。残さないと、その時点で他の候補が消えて選び直しができなくなる。機構は単純で、brand 軸の件数を集計するときだけ、brand の絞り込み条件をフィルタから外せばよい。チェックボックスで複数選択できる UI では必須の処理である。
- **集計コスト**：件数の集計はマッチした全件を走査するため負荷が大きい。ファセットを別エンドポイントに分ける、集計対象のフィールドをサーバー側の許可リストで絞る、件数が不要なら計算を省略できるオプションにする、といった逃げ道を設計に入れておく。
- **権限による情報の漏えい**：閲覧権限のないアイテムを件数に含めると、その存在自体が推測されてしまう。ファセットの集計にも、検索結果と同じ認可フィルタをかける。

近似に依存する実装もある点には注意が要る。
Azure AI Search のドキュメントは、シャード分割されたインデックスでは各シャードが上位 N 件だけを返してから統合するため、ファセットの件数が実際より少なく数えられる場合があると明記している。
正確な件数が要るときは count を十分大きく取るよう案内されており、分散検索基盤のファセット計算は一般に精度とコストのトレードオフがある。

## 主要な検索 API のファセット対応

| API | 指定方法 | レスポンス |
|---|---|---|
| Azure AI Search | クエリの `facets` パラメータにフィールド名を並べる | `@search.facets` |
| Elasticsearch | `aggs`（aggregations）で集計を定義する | `aggregations` |
| Solr | `facet=true` と `facet.field=brand` | `facet_counts` |
| Algolia | `facets` リクエストパラメータに属性名 | `facets` |

## HATEOAS の制約

HATEOAS は、Fielding が REST を定式化した博士論文（2000年）の第5章で、統一インターフェース（uniform interface）を構成する4つの制約のひとつとして定められた。
クライアントが事前に知ってよいのは入口の URL だけで、それ以降の操作はすべてサーバーがレスポンスに埋め込んだリンクを選んで進む、という原則である。
アプリケーションの状態遷移を推進するエンジンがハイパーメディアの中にある、というのが名前の由来である。

具体例として、注文リソースを考える。
未発送の状態では、レスポンスにキャンセルと支払いのリンクが含まれる。

```json
{
  "id": 1234,
  "status": "pending",
  "_links": {
    "self":    { "href": "/orders/1234" },
    "cancel":  { "href": "/orders/1234/cancel" },
    "payment": { "href": "/orders/1234/payment" }
  }
}
```

発送が済むと、キャンセルのリンクは消え、代わりに追跡用のリンクが現れる。

```json
{
  "id": 1234,
  "status": "shipped",
  "_links": {
    "self":  { "href": "/orders/1234" },
    "track": { "href": "/orders/1234/tracking" }
  }
}
```

この設計では、「発送後はキャンセルできない」という業務ルールをクライアントに実装する必要がない。
リンクの有無がそのまま操作の可否を表し、クライアントは `cancel` があればボタンを出す、とだけ決めればよい。
サーバーが URL スキームを変えてもクライアントは壊れず、新しい操作はリンクの追加で告知できる。

## Richardson 成熟度モデルと現実の落としどころ

HATEOAS の位置づけを考えるのに便利なのが、**Richardson 成熟度モデル**（Richardson Maturity Model）である。
Leonard Richardson がカンファレンスでの講演で提唱し、Martin Fowler の記事で広まった分類で、REST 風味の度合いを4段階で見る。

| レベル | 内容 |
|---|---|
| 0 | HTTP をトンネルにした RPC 的な呼び出し。単一の URL に POST を送りつける |
| 1 | リソースを導入し、対象ごとに URL を分ける |
| 2 | HTTP メソッドとステータスコードを規則どおりに使う |
| 3 | ハイパーメディア制御（HATEOAS）を導入する |

原理主義の側からは厳しい見方がある。
Fielding はブログ記事「REST APIs must be hypertext-driven」（2008年）で、ハイパーテキスト駆動でないものは REST API と呼ぶべきでないと明言し、Fowler の記事もレベル3 が REST の前提条件だという Fielding の見解を紹介している。

ただし実際の現場では、REST API と呼ばれるものの大半はレベル2どまりである。
クライアント側に汎用的なリンク解釈の層を作るコストがかかること、レスポンスが肥大すること、フロントエンドの操作が事前に決まっていて固定実装になりがちなことが、その理由として挙げられる。
レベル3 を目指す場合のリンク表現には標準もあり、HAL（JSON Hypertext Application Language）は `_links` と `_embedded` を定義する軽量なメディアタイプで、JSON:API はリレーションシップとリンクの仕様を持つ。

## ファセットと HATEOAS の接点

ファセットの各候補は、現在の検索状態から取りうる次の遷移そのものである。
したがって各値をリンクつきで返すと、絞り込み UI がそのまま HATEOAS 式になる。

```json
{ "value": "Nike", "count": 12, "href": "/products?q=sneakers&brand=Nike" }
```

この形では、クライアントは「どのパラメータ名で絞り込むか」という URL の組み立て規則を知らなくて済む。
サーバー側がパラメータ設計を変えても、クライアントはリンクをたどるだけで追従できる。

## 別文脈の「facet」

OData（Microsoft 系の API 標準）のスキーマ定義言語 CSDL にも facet という語が出るが、こちらはプロパティに付随するメタデータ属性（Nullable、MaxLength、Precision など）を指し、検索のファセットとは別物である。

## 出典

- [Chapter 5: Representational State Transfer (REST) | Fielding, Architectural Styles and the Design of Network-based Software Architectures](https://www.ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm)
- [Richardson Maturity Model | Martin Fowler](https://martinfowler.com/articles/richardsonMaturityModel.html)
- [REST APIs must be hypertext-driven | Roy T. Fielding](https://roy.gbiv.com/untangled/2008/rest-apis-must-be-hypertext-driven)
- [Add Facets to a Query | Microsoft Learn (Azure AI Search)](https://learn.microsoft.com/en-us/azure/search/search-faceted-navigation)

## 関連ノート

- [タクソノミーとは（ソフトウェアの文脈）](../2026-08-24-software-taxonomy/README.md)
