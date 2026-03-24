+++
title = "解説：ABC155 D - Pairs"
date = "2024-05-01"
[taxonomies]
category = ["競プロ"]
tags = ["Rust"]
[extra]
comment = true
+++

## 問題

### 概要

$N$ 個の整数 $A_1, A_2, \ldots, A_N$ が与えられる．このうち $2$ つを選んで積をとったものは $\frac{N(N-1)}{2}$ 通り存在するが，このうち小さい方から $K$ 番目の数を求めよ．

- $2 \le N \le 2\times 10^5$
- $1 \le K \le \frac{N(N-1)}{2}$
- $-10^9 \le A_i \le 10^9$

### リンク

- [ABC155 D - Pairs (AtCoder)](https://atcoder.jp/contests/abc155/tasks/abc155_d)

## 解説

### 考察

愚直な実装（ペアを列挙してソートする）はすぐに思いつきますが，
$N \le 2\times 10^5$ であるので，すべてを列挙するのはもちろん不可能です．

このように，解の候補が取りうる値が非常に多いタイプの問題でよく使うテクニックとして，**「解の存在性で二分探索をする」** というものがあります．

---

まず，この問題より少し簡単な

> $A_1,\ldots,A_N$ のペアの積のうち，$x$ 未満であるものはいくつあるか

という問題（問題<sup>\*</sup>）を考えてみます．このとき，以下の性質が成り立ちます．

{% admonition(type="note", title="性質1") %}
**$A_1,\ldots,A_N$ のペアの積のうち，$x$ 未満であるもの** がちょうど $K$ 個であるとき，$x$ が $K$ 番目に大きい数である．
{% end %}

$x$ が増えると，**$A_1,\ldots,A_N$ のペアの積のうち，$x$ 未満であるもの** は単調に増えていくため，これがちょうど $K$ 個になるような $x$ の値は二分探索によって高速に求めることができます．

よって，問題<sup>\*</sup> を速く解くことができれば，性質 1 を使うことで元の問題の答えを求められることがわかります．

### 問題<sup>\*</sup> を解く

簡単のため，$A_i \ge 0$ とします．問題<sup>\*</sup> では，

$$
A_i \times A_j < x \quad (1 \le i \lt j \le N)
$$

を満たすような添字の組 $(i,j)$ の数を数えればよいです．

これは，あらかじめ $A$ をソートしておくことで，すべての $i$ に対して $j$ を二分探索することができ，$O(N\log N)$ で求めることが可能です．

$A_i < 0$ の場合にも，$j$ を逆向きに見ていくことで同様の手法を用いることができます．

### 計算量

問題<sup>\*</sup> を解くのに $O(N\log N)$ 時間，性質 1 を使って解を探すのに $O(\log (\max A_i))$ 回かかるので，全体では $O(N\log N \log (\max A_i))$ 時間となります．

結構ギリギリです．（Python とかだと間に合わないかも？）

### コード

`Rust`での AC コードは以下のとおりです．

```rs
use proconio::{
    input,
    marker::{Bytes, Chars, Usize1},
};

const NEG1: usize = 1_usize.wrapping_neg();
const INF: isize = 1001001001001001001;

fn main() {
    input! {
        N: usize,
        K: Usize1,
        mut A: [isize; N]
    }

    // Aをソート
    A.sort();

    // A[i] * A[j] がx未満である(i,j)の個数を数える
    let count = |x: isize| -> usize {
        let mut ans = 0;
        for i in 0..N {
            if A[i] >= 0 {
                let mut ok = NEG1;
                let mut ng = N;
                while ng.wrapping_sub(ok) > 1 {
                    let mid = ok.wrapping_add(ng) / 2;
                    if A[i] * A[mid] < x {
                        ok = mid;
                    } else {
                        ng = mid;
                    }
                }
                // i == j となる場合を除外
                if ok != NEG1 && i <= ok {
                    ans += ok;
                } else {
                    ans += ok.wrapping_add(1);
                }
            } else {
                let mut ok = NEG1;
                let mut ng = N;
                while ng.wrapping_sub(ok) > 1 {
                    let mid = ok.wrapping_add(ng) / 2;
                    if A[i] * A[N - mid - 1] < x {
                        ok = mid;
                    } else {
                        ng = mid;
                    }
                }
                // i == j となる場合を除外
                if ok != NEG1 && N.wrapping_sub(ok) - 1 <= i {
                    ans += ok;
                } else {
                    ans += ok.wrapping_add(1);
                }
            }
        }
        ans / 2
    };

    let mut ok = -INF;
    let mut ng = INF;

    while ng - ok > 1 {
        let mid = (ok + ng) / 2;

        if count(mid) <= K {
            ok = mid;
        } else {
            ng = mid;
        }
    }

    println!("{ok}");
}
```

### 提出

実行時間：`453ms`（log が 2 つついているので遅めです）

- [https://atcoder.jp/contests/abc155/submissions/52989734](https://atcoder.jp/contests/abc155/submissions/52989734)
