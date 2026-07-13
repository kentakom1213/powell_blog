+++
title = "LT会で知ったことまとめ"
date = "2022-05-27"
draft = true
[taxonomies]
category = ["プログラミング"]
tags = []
+++

バイト先で行った LT 会 (LightningTalk: 短めのプレゼン) で新しい知見を得たので取り急ぎまとめます。
間違ってたことを言ってたらご指摘お願いします。

<!-- more -->

## git の機能

### git submodule

git のプロジェクトの中にさらにプロジェクトを生成できる。
入れ子構造を別個に git 管理できるみたい。

[Git-submodule の押さえておきたい理解ポイントのまとめ Qiita](https://qiita.com/kinpira/items/3309eb2e5a9a422199e9)

## VisualStudioCode 関係

### vscode remote-ssh

ssh 接続先に vscode から接続できる。
ファイル生成とか編集とかを、コマンドを介さずに行える。

[Remote Development using SSH](https://code.visualstudio.com/docs/remote/ssh)

### vscode remote-containers

上と同様に、Docker コンテナに vscode 側から接続できる。
イメージのビルドからコンテナを立てて接続するまでを、全て vscode 上で完結させられる。

[VSCodeRemoteContainer が良い Qiita](https://qiita.com/d0ne1s/items/d2649801c6f804019db7)

### vscode live share

vscode の画面をリアルタイムで共有できる拡張機能。
コードの同時編集だけでなく、ターミナルを共有したり、ローカルサーバーへの接続を共有したりみたいなこともできる。
チャットとか音声通話機能もついてる。至れり尽くせり。Microsoft 様様。

[Collaborate with LiveShare](https://code.visualstudio.com/learn/collaboration/live-share)

### TabNine

いろんなコードを AI が学習して、候補を出してくれる。
まだ試したことないけどすごいらしい。
GithubCopilot に似てる？？

[TabNine](https://www.tabnine.com/)

---

## 便利ツール

### Obsidian

Markdown でノートをとれる。iCloud を使うとデバイス間での共有ができるらしい。
めんどくさいので自分は git で共有している。

[Obsidian](https://obsidian.md/)

### Mermaid

Markdown にフローチャートとか ER 図とかを埋め込めるすごいやつ。

$\downarrow$ 詳しくはこちら
[Mermaid 入門](https://github.com/kentakom1213/share/blob/main/documents/mermaid.pdf)

### fzf

コマンドラインの履歴検索みたいな機能をつけられるらしい。
導入してみたい。

[fzf を活用して Terminal の作業効率を高める](https://qiita.com/kamykn/items/aa9920f07487559c0c7e)

## まとめ

やたら盛り上がっておもしろかった。他にも何か面白い機能とかツールあったら教えてください。
