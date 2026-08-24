---
title: tombstone（削除マーカー）とは
date: 2026-08-24
updated: 2026-08-24
tags: [tombstone, soft-delete, database, distributed-systems, cassandra, kafka]
related: []
---

# tombstone（削除マーカー）とは

## 概要

データベースやメッセージング基盤に「このデータを消したい」と伝えるとき、対象を即座に物理削除する代わりに、「消えた」という印だけを書き込んでおく方式がある。
その印を **tombstone**（削除マーカー）と呼ぶ。[^etym]
データ本体の除去は後段の整理処理に任せ、墓石自体も最終的にはそこで回収される。
ソフトデリートに近い発想であるが、文脈によって具体的な姿が異なる。

[^etym]: tombstone は英語で「墓石」を意味する一般名詞であり、消えたデータの墓標という比喩である。

## 基本的な動作

削除の要求は墓石の書き込みとして処理され、読み取り側は墓石を見て削除済みと判断する。
本体の物理的な除去は遅延される。

```
書き込み:  {key: "user1", value: "kotaro"}    ← データ本体
削除要求:  {key: "user1", tombstone: true}    ← 墓石として追記
回収:      コンパクション等で本体と墓石をまとめて除去
```

## なぜ墓石を残すのか

本体ごと消してしまわない理由は一つではない。
主なものを腑分けすると次のとおりである。

- **削除の伝播**：分散環境で本体を即時削除すると、削除に気づいていない複製ノードからデータが復活する（Cassandra はこの現象を「ゾンビ」と呼ぶ）。墓石が残っていれば、後から復旧したノードにも「消えた」という事実を伝えられる。
- **追記型ストレージとの相性**：LSM ツリー（書き込みを順次追記して後で整理するストレージ構造）では既存データの書き換えができないため、削除も墓石の追記として表現する必要がある。
- **証跡の保持**：GDPR の「忘れられる権利」のような要請では、個人情報そのものは消す一方、「いつ削除要求があって消したか」の記録は残したい。ID と削除日時だけを持つ墓石がこの両立を可能にする。
- **参照整合性**：他のデータから参照されている行を物理削除すると参照が壊れるが、墓石として残せば「削除済みのユーザー」といった表示に置き換えられる。

## 文脈ごとの姿

- **分散データベース（Cassandra）**：DELETE は墓石の書き込みとして処理される。墓石には猶予期間（`gc_grace_seconds`、デフォルト10日）があり、期間を過ぎたものがコンパクションで本体ごと回収される。
- **メッセージング（Kafka）**：ログ圧縮を有効にしたトピックで、あるキーに値が null のメッセージを書き込むと墓石として扱われ、同じキーの古いメッセージが除去対象になる。
- **イベント駆動・DDD**：集約の削除を削除イベントとして発行し、それを購読する read model（検索・表示用に複製されたデータ）が投影を消す。この削除イベントが墓石の役割を果たす。
- **RDB の論理削除**：`deleted_at` 列に時刻を入れる方式と対比される形で、本体の行を消して ID と削除日時だけを持つ抜け殻テーブル（墓石テーブル）に残す方式を tombstone 方式と呼ぶことがある。

## ソフトデリートとの違い

広義には墓石方式もソフトデリート（論理削除）の一種だが、実務の対比では「本体を残すか、消すか」が分かれ目になる。

| | `deleted_at` 方式 | tombstone 方式 |
|---|---|---|
| データ本体 | 残る | 消す（ID と削除日時程度のみ残す） |
| 復元 | 可能 | 基本的に不可能 |
| クエリへの影響 | `WHERE deleted_at IS NULL` を全クエリに必要 | 墓石は別テーブルに隔離できる |

復元の要件があるなら `deleted_at` 方式が向く。
法的な削除義務への対応や、参照整合性を保ちつつ本体を消したい場合は tombstone 方式が向く。

## 運用上の注意

墓石の蓄積は性能劣化の元になる。
読み取りが多くの墓石を跨がなければならないためで、Cassandra では墓石の増加によるクエリ劣化がよく知られた落とし穴である。
回収はコンパクション次第なので、大量削除を伴う設計では回収状況の監視が要る。
また tombstone 方式は基本的に元に戻せないため、採用前に復元要件の有無を確認する。

## GitHub で「消えた」ときに残るもの

GitHub でコンテンツが消える際に墓石が残るかどうかは、消され方で異なる。

- **リポジトリの完全削除**：墓石は残らない。URL は単に 404 を返す。
- **DMCA テイクダウン**：「This repository is currently disabled due to a DMCA takedown notice.」というページが残り、通知書自体は [github/dmca](https://github.com/github/dmca) リポジトリに公開アーカイブされる。
- **他サービスへの移転**：「moved to ...」だけを書いた README の抜け殻を残す運用があり、これは俗に墓石リポジトリと呼ばれる。
- **ユーザーアカウントの削除**：削除されたアカウントのコメントやコミットは [ghost](https://github.com/ghost) ユーザーに付け替えられる。発言者を墓石化して発言自体を残す仕組みである。

## サンプルコード

RDB での tombstone 方式のデモである。
本体テーブルの行は DELETE し、墓石テーブルには ID と削除日時だけを残す。
完全版は同じディレクトリの `demo.sql` で、SQLite での実行確認済みである。

```sql
-- 退会処理（抜粋）：本体は消し、墓石だけを挿入する
BEGIN;
INSERT INTO user_tombstones (user_id, deleted_at)
  VALUES (1, '2026-08-24 10:00:00');
DELETE FROM users WHERE id = 1;
COMMIT;
```

実行と結果は次のとおりである。

```console
$ sqlite3 -header -column < demo.sql
id  item    ordered_by        
--  ------  ------------------
1   リンゴ  (削除済みユーザー)
2   バナナ  hanako            
```

## 出典

- [Tombstones | Apache Cassandra Documentation](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/compaction/tombstones.html)
- [Apache Kafka Documentation - Log Compaction](https://kafka.apache.org/documentation/#compaction)
- [github/dmca | GitHub](https://github.com/github/dmca)
- [@ghost | GitHub](https://github.com/ghost)
