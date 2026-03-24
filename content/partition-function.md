+++
title = "分割数"
date = "2022-07-02"
description = ""
[taxonomies]
category = ["競プロ"]
tags = ["数学", "アルゴリズム", "Python"]
[extra]
comment = true
+++

- 参考：[分割数と、問題まとめ](https://drken1215.hatenablog.com/entry/2018/01/16/222843)

{% admonition(type="note") %}
自然数を $0$ 以上の整数に分割する場合の数  
$P(n, k)$ で表す
{% end %}

### パターン

- 「$k$ 個の $1$ 以上の整数への分割」→ $P(n-k, k)$ 通り
- 「任意の個数の $1$ 以上の整数への分割」→ $P(n, n)$ 通り

### 計算量

- $P(n, k) \rightarrow O(nk)$
- $P(n, n) \rightarrow O(n\sqrt(n))$

### 漸化式

$$
\begin{align*}
P(n, k) = P(n, k-1) + P(n-k, k)
\end{align*}
$$

#### 導出

$Q(n, k)$  
$\rightarrow$ ($n$を$k$個の$1$以上の整数に分割する場合の数)  
$\rightarrow$ ($n - k$を$k$個の$0$以上の整数に分割する場合の数)  
$\rightarrow$ $P(n-k, k)$

1. $0$を含むもの  
   $1$つの$0$を取り除き、残りの$k-1$個を$0$以上の和で表す方法をを調べれば良い → $P(n, k-1)$通り
2. $0$を含まないもの  
   $n$を$1$以上の整数$k$個に分割する場合の数 → $P(n-k, k)$通り

### 実装

```python
def init_array(i, j, val=0): return [[val]*j for _ in range(i)]
```

```python
N, K = 5, 3
dp = init_array(N+1, K+1, 0)
dp[0][0] = 1

for n in range(N+1):
    for k in range(1, K+1):
        if n - k >= 0:
            dp[n][k] = dp[n][k-1] + dp[n-k][k]
        else:
            dp[n][k] = dp[n][k-1]

print(*dp, sep="\n")
print(dp[N][K])

# ---- out -----
# 5
# 5 = 5+0+0
#   = 4+1+0
#   = 3+2+0
#   = 3+1+1
#   = 2+2+1
```
