---
title: Amazon Inspector とは
date: 2026-08-25
updated: 2026-08-25
tags: [aws, security, amazon-inspector, vulnerability-management, cloud-security]
related: []
---

# Amazon Inspector とは

## 概要

**Amazon Inspector** は AWS の脆弱性管理サービスで、環境内のワークロードを自動検出し、ソフトウェアの脆弱性と意図しないネットワーク公開（外部から到達可能なポート）を継続的にスキャンする。
従来型のスキャナーのようにスケジュールを組む必要はなく、リソースの変更や新しい CVE[^cve] の公開といったイベントに反応して再スキャンが自動で走る。
2021年にフルリニューアルされており、API やコンソールの内部名称には inspector2 / v2 が使われている。

[^cve]: CVE（Common Vulnerabilities and Exposures）は、公知の脆弱性に一意の ID を付与する仕組み。「CVE-2026-12345」のような識別子で個別の脆弱性を指す。

## スキャン対象

- **EC2 インスタンス**：OS パッケージの脆弱性とネットワーク到達性
- **ECR のコンテナイメージ**：イメージ内パッケージの脆弱性（push 時に自動スキャンされ、その後も継続して再スキャンされる）
- **Lambda 関数・レイヤー**：依存パッケージの脆弱性に加え、コード自体のスキャン（インジェクションや機密情報の埋め込みなどの検査）にも対応
- **コードリポジトリ**：アプリケーションコードや IaC（Terraform のような構成コード）のセキュリティ検査
- Azure の VM、Function Apps、Container Registry（ACR）も対象。料金ページの記載上、マルチクラウドに対応している

## EC2 の2つのスキャン方式

EC2 のパッケージ脆弱性スキャンには、エージェントベースとエージェントレスの2方式がある。
初回の有効化時は両方式を併用するハイブリッドモードに自動で登録される。

- **エージェントベース**：SSM（AWS Systems Manager、EC2 を一元管理するサービス）のエージェントでソフトウェアのインベントリを収集する。新規インスタンスの起動やソフトウェアのインストール、関連 CVE の追加といったイベントで即座に再スキャンされる継続型である。Linux では deep inspection により言語パッケージの脆弱性まで検出できる。前提として、インスタンスが SSM の管理対象になっている必要がある
- **エージェントレス**：EBS スナップショットを作成し、EBS direct API で中身を読み取って評価したあと、スナップショットを削除する。SSM 管理外のインスタンスが対象で、24時間ごとにスキャンされる。EBS バックアップでファイルシステムが ext3、ext4、xfs のいずれか、ボリューム数が8個未満で合計1200GB以下、という制約がある

ネットワーク到達性のスキャンは12時間ごとに実施される。
スキャン対象から外したいインスタンスには `InspectorEc2Exclusion` タグを付ける。
除外したインスタンスには課金されない。

## finding と Inspector Risk Score

脆弱性やネットワーク露出が見つかると **finding**（検出結果）が作られる。
finding には問題の詳細、影響を受けるリソース、修正の推奨手順が含まれ、修正が完了したことは Inspector 側が検知して自動でクローズする。
対応しない finding は抑制ルール（suppression rule）で一覧から隠せ、CSV や JSON のレポート出力もできる。

優先度付けのための指標として **Inspector Risk Score** がある。
NVD（National Vulnerability Database）が公表する CVSS[^cvss] のベーススコアを、自分の環境に合わせて補正したもので、たとえば「ネットワーク越しに悪用可能な脆弱性だが、その EC2 インスタンスはインターネットから到達不能」ならスコアが下がる。
理論上の深刻度と実環境でのリスクを分けてくれるので、対応順位のノイズが減る。

[^cvss]: CVSS（Common Vulnerability Scoring System）は、脆弱性の深刻度を0から10までの数値で表す共通尺度。

## 組織管理と他サービスとの連携

AWS Organizations を使っている場合は、委任管理者アカウントから全メンバーアカウントの Inspector を一元管理できる。
組織への新規参加アカウントに対して自動で有効化する設定も用意されている。

finding は EventBridge にイベントとして発行され、Lambda や SNS にルーティングしてほぼリアルタイムの自動対応に組み込める。
AWS Security Hub CSPM を有効化していれば、Inspector の finding は自動的に Security Hub にも集約される。

このほか、SBOM（ソフトウェア部品表）のエクスポートや、EC2 に対する CIS ベンチマーク（Center for Internet Security によるセキュリティ構成の業界標準）の評価機能もある。
CIS 評価はオンデマンド実行で、評価ごとの課金になる。

## 料金モデル

スキャンしたワークロードに対する従量課金で、ワークロードの種別ごとに課金単位が異なる。
EC2 は月内の平均インスタンス数（断続的に起動するものは実行時間で按分）、ECR イメージは push 時の初回スキャンと再スキャン回数、CIS 評価はインスタンスごとの評価回数で課金される。
Jenkins などの CI/CD ツールから実行するオンデマンドのイメージスキャンも課金対象である。
無料トライアルがある。具体的な単価は料金ページで確認する。

## 類似サービスとの棲み分け

- **Inspector**：脆弱性管理。環境のどこに穴があるかを見つける
- **GuardDuty**：脅威検知。今まさに起きている不審な挙動を見つける
- **Security Hub**：セキュリティ情報の集約。Inspector など複数サービスの結果を受け止め、ベンチマークとの照合を行う

## 出典

- [Amazon Inspector（製品ページ）](https://aws.amazon.com/inspector/)
- [What is Amazon Inspector? | AWS Documentation](https://docs.aws.amazon.com/inspector/latest/user/what-is-inspector.html)
- [Scanning Amazon EC2 instances | AWS Documentation](https://docs.aws.amazon.com/inspector/latest/user/scanning-ec2.html)
- [Amazon Inspector pricing](https://aws.amazon.com/inspector/pricing/)
