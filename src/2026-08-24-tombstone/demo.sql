-- tombstone（削除マーカー）方式の動作デモ
-- 本体テーブルからは行を消し、「消えた」という印だけを別の墓石テーブルに残す。
-- SQLite でそのまま実行できる（外部キー制約は簡単のため有効化していない）。

CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL
);

-- 墓石テーブル：ID と削除日時だけを持つ抜け殻
CREATE TABLE user_tombstones (
  user_id INTEGER PRIMARY KEY,
  deleted_at TEXT NOT NULL
);

CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users (id),
  item TEXT NOT NULL
);

INSERT INTO users (id, name) VALUES (1, 'kotaro'), (2, 'hanako');
INSERT INTO orders (user_id, item) VALUES (1, 'リンゴ'), (2, 'バナナ');

-- ユーザー1を退会させる。
-- 本体は DELETE し、tombstone だけを挿入する。
BEGIN;
INSERT INTO user_tombstones (user_id, deleted_at) VALUES (1, '2026-08-24 10:00:00');
DELETE FROM users WHERE id = 1;
COMMIT;

-- 過去の注文を表示する。
-- 本体行があれば名前を、墓石だけ残っていれば「削除済み」と表示できる。
SELECT
  o.id,
  o.item,
  CASE
    WHEN u.name IS NOT NULL THEN u.name
    WHEN t.user_id IS NOT NULL THEN '(削除済みユーザー)'
    ELSE '(不明)'
  END AS ordered_by
FROM orders o
LEFT JOIN users u ON u.id = o.user_id
LEFT JOIN user_tombstones t ON t.user_id = o.user_id
ORDER BY o.id;
