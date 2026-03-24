+++
title = "高速フーリエ変換（FFT）- 実装編"
date = "2022-10-04"
description = "FFTを実装したい (3/3)"
[taxonomies]
category = ["FFT"]
tags = ["数学", "アルゴリズム", "Python"]
[extra]
comment = true
+++

FFT の`Python3`での実装を目指します。

## 参考

- [FFT(高速フーリエ変換):実装のための数式と実装例](https://qiita.com/k-kotera/items/4fe20c48be56d2eb4ba4)
- [FFT を訪ねて［後編］Python と C++で作ってみる](https://negligible.hatenablog.com/entry/2021/11/13/025822)

## 回転因子（配列）

入力の配列サイズ $N$ に対して、$N/2$ サイズの回転因子を用意すれば良い。

サイズ $N$ の回転因子の配列を $W_N$ とすると、

$W_N[n] = e^{-2\pi i\frac{n}{N}}$ であるので、

```python
import numpy as np

W_N = np.exp(-2j * np.pi * np.arange(N // 2) / N)
```

## FFT

関数は下のようなフローとなる。

**FFT**（入力配列`x`）

1. 入力配列を偶数行、奇数行に分割 →`x_even`、`x_odd`
2. 偶数行、奇数行のバタフライ演算を再帰的に計算 →`F_even`、`F_odd`
3. 出力配列を用意 →`F`
4. 回転因子の配列を用意 →`W`
5. 出力配列の前半分を`F_even + W*F_odd`とする
6. 出力配列の後半分を`F_even - W*F_odd` とする

↓ 実際のコード（[参考サイト](https://qiita.com/k-kotera/items/4fe20c48be56d2eb4ba4)）

```python
import numpy as np

def FFT(X):
    N = len(X)
    n = N // 2

    # 終了条件
    if N == 1:
        return X

    # 再帰的にFFTを計算
    F_even = FFT(X[0::2])
    F_odd = FFT(X[1::2])

    # 回転因子
    W = np.exp(-2j * np.pi * np.arange(n) / N)

    # バタフライ演算
    F = np.zeros(N, dtype='complex')
    F[:n] = F_even + W * F_odd
    F[n:] = F_even - W * F_odd

    return F
```

## IFFT

逆高速フーリエ変換（高速フーリエ逆変換？）

$$
X = \frac{1}{N}\sum_{n=0}^{N-1} F[n]\~ e^{2i\pi k\frac{n}{N}}
$$

↑ これを実装すればいいので，コード自体は FFT とそんなに変化なし．
回転因子の $i$ の符号を逆にして，最後に $1/N$ をかけるだけです．

```python
import numpy as np

def IFFT(F, origin=1):
    N = len(F)
    n = N // 2

    # 終了条件
    if N == 1:
        return F

    # 再帰的にFFTを計算
    X_even = IFFT(F[0::2], 0)
    X_odd = IFFT(F[1::2], 0)

    # 回転因子（IFFTなので 2*pi*i）
    W = np.exp(2j * np.pi * np.arange(n) / N)

    # バタフライ演算
    X = np.zeros(N, dtype='complex')
    X[:n] = X_even + W * X_odd
    X[n:] = X_even - W * X_odd

    if origin:
        X /= N

    return X
```

## テスト

`numpy.fft` モジュールを使って検算をしてみます．

### テストコード

```python
print("# 入力配列")
X = np.array([1, 4, 3, 2, 0, 8, 4, 7])
print(X)

print("\n# FFTの実行結果")
F = FFT(X)
print(F)

print("\n# IFFTの実行結果")
X_ = IFFT(F)
print(X_)

print("\n# numpyでのFFT")
F_numpy = fft.fft(X)
print(F_numpy)

print("\n# numpyでのIFFT")
X_numpy = fft.ifft(F_numpy)
print(X_numpy)
```

### 結果

```
# 入力配列
[1 4 3 2 0 8 4 7]

# FFTの実行結果
[ 29.        +0.j           1.70710678+7.36396103j
  -6.        -3.j           0.29289322+5.36396103j
 -13.        +0.j           0.29289322-5.36396103j
  -6.        +3.j           1.70710678-7.36396103j]

# IFFTの実行結果
[1.+0.0000000e+00j 4.-4.5924255e-17j 3.+3.0616170e-17j 2.+4.5924255e-17j
 0.+0.0000000e+00j 8.-4.5924255e-17j 4.-3.0616170e-17j 7.+4.5924255e-17j]

# numpyでのFFT
[ 29.        +0.j           1.70710678+7.36396103j
  -6.        -3.j           0.29289322+5.36396103j
 -13.        +0.j           0.29289322-5.36396103j
  -6.        +3.j           1.70710678-7.36396103j]

# numpyでのIFFT
[1.+0.j 4.+0.j 3.+0.j 2.+0.j 0.+0.j 8.+0.j 4.+0.j 7.+0.j]
```

けっこう良さそう！！
