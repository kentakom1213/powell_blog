+++
title = "Next.jsでポートフォリオサイトを作ってみた"
date = "2023-04-26"
updated = "2024-04-27"
[taxonomies]
category = ["プログラミング"]
tags = ["Web開発"]
[extra]
cover_image = "/images/portfolio-nextjs/skills.png"
+++

Next.js と React でポートフォリオサイトを作成してみました。

<!-- more -->

## 概要

{% admonition(type="note", title="開発環境") %}

- 開発言語：[TypeScript](https://www.typescriptlang.org/)
- フレームワーク
  - [Next.js](https://nextjs.org/)
  - [React](https://react.dev/)
  - [styled components](https://styled-components.com/)
- デプロイ：[Vercel](https://vercel.com/)
- 開発環境：
  - MacbookAir（M1 チップ）（Ventura 13.0）

{% end %}

- リポジトリ：[kentakom1213/portfolio-nextjs](https://github.com/kentakom1213/portfolio-nextjs)

<!--- ポートフォリオ：[portfolio.pwll.dev](https://portfolio.pwll.dev)-->

---

## デザイン

Figma でデザインをしました。ポートフォリオサイトらしく、

- 自己紹介
- スキル
- 経験
- お問い合わせ

ページを追加。デザインはこんな感じです。

{{ image(path="/images/portfolio-nextjs/design.png", width=700) }}

なるべくシンプルかつかわいいデザインになるように腐心しました。

## コーディング

ページ作成を React、スタイルは styled components で行いました。
最近はスタイル作成に tailwind CSS を使う例が多いようですが、個人的に
tailwind CSS を含んだコードの見た目があまり好きではないため、
styled components を利用しています。
（ただ、レスポンシブ対応を 1 から書くのがキツかったので今後はそっちを採用したい気持ちです）

### about ページ

どの写真を使うか結構悩みました。

{{ image(path="/images/portfolio-nextjs/about.png", width=700) }}

### skills ページ

並べるデザインのレスポンシブ対応にちょっと苦労しました。
このあたりの面倒臭さを考えると、素直に tailwind CSS を使うのがいいのかも。

{{ image(path="/images/portfolio-nextjs/skills2.png", width=700) }}

### experience ページ

このページに一番手がかかっています。
css の grid の使い方の勉強にもなりました。

{{ image(path="/images/portfolio-nextjs/experience.png", width=700) }}

### contact ページ

[formspree](https://formspree.io/)というサービスを利用しました。
Google フォームの埋め込みとは違い、自分で見た目をカスタマイズできるので便利です。

{{ image(path="/images/portfolio-nextjs/contact.png", width=700) }}

## デプロイ

Vercel にアカウントを作って、GitHub のリポジトリを紐付けるだけで
勝手にデプロイしてくれます！Vercel 便利！

## まとめ

デザインを含めて 1 から一人で手作りしたのは初めてだったのですが、なかなかいい経験になりました。
我ながらいい感じにできたと思います。

次はフロント Next.js、バックエンド Axum とかのアプリを作ってみようかな
