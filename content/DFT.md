+++
title = "離散フーリエ変換（DFT）"
date = "2022-10-02"
description = "FFTを実装したい (1/3)"
[taxonomies]
category = ["FFT"]
tags = ["数学", "アルゴリズム"]
[extra]
comment = true
+++

自分が理解するためのメモ書きのようなものなので、以下の記事 ↓ の下位互換のような記事になってます。

## 参考

- [離散フーリエ変換（DFT）- Cognicull](https://cognicull.com/ja/f5q2jl62)
- [離散フーリエ変換(DFT)の仕組みを完全に理解する - Qiita](https://qiita.com/TumoiYorozu/items/5855d75a47ef2c7e62c8) ← この説明が好き
- [高速フーリエ変換 FFT を理解する](https://qiita.com/bellbind/items/ba7aa07f6c915d400000)

## 離散フーリエ変換とは

> 離散フーリエ変換では、**時系列データが N 個**な場合、区間 N で 1/2 周期とする周波数を基本に、0 倍(定数成分)から N-1 倍までの**N 個の周波数成分**を算出します。

フーリエ変換は、「関数を無限次元のベクトルとみたときの基底変換」と言うことができる。このとき、時間を離散的に（とびとびの値）として表すと、これはただのベクトルの基底変換と言える。

つまり、与えられたベクトルを $\sin,\cos$ をもとに生成された基底に基底変換することが離散フーリエ変換である。

---

{% admonition(type="note", title="フーリエ変換") %}

- 入力、出力が（複素）関数
- $F: (\mathbb{C}\mapsto\mathbb{C})\mapsto(\mathbb{C}\mapsto\mathbb{C})$
  {% end %}

{% admonition(type="note", title="離散フーリエ変換") %}

- 入力、出力が（複素）ベクトル
- $F: \mathbb{C}^n\mapsto\mathbb{C}^n$
  {% end %}

## 導出

### sin, cos の離散化

$\sin\frac{2k\pi}{N}\theta,\cos\frac{2k\pi}{N}\theta$ をサンプリングし、ベクトルとして表してみる。

※ベクトルの次元とサンプリング数を同じにするのは、逆変換したときに同じ形になるようにするため

（$N=4,\~k=\lbrace 0,1,2,3\rbrace,\~\theta=\lbrace 0,1,2,3\rbrace$）

#### sin

$$
\begin{align*}
	\begin{array}{cccccc}
		\theta & & 0 & 1 & 2 & 3 \\\\
		\hline
    \sin{\frac{0\pi}{4}\theta} & =( & 0 & 0 & 0 & 0 & )\\\\
    \sin{\frac{2\pi}{4}\theta} & =( & 0 & 1 & 0 & -1 & )\\\\
    \sin{\frac{4\pi}{4}\theta} & =( & 0 & 0 & 0 & 0 & )\\\\
    \sin{\frac{6\pi}{4}\theta} & =( & 0 & -1 & 0 & 1 & )
  \end{array}
\end{align*}
$$

#### cos

$$
\begin{align*}
	\begin{array}{cccccc}
		\theta & & 0 & 1 & 2 & 3 \\\\
		\hline
    \cos{\frac{0\pi}{4}\theta} & =( & 1 & 1 & 1 & 1 & )\\\\
    \cos{\frac{2\pi}{4}\theta} & =( & 1 & 0 & -1 & 0 & )\\\\
    \cos{\frac{4\pi}{4}\theta} & =( & 1 & -1 & 1 & -1 & )\\\\
    \cos{\frac{6\pi}{4}\theta} & =( & 1 & 0 & -1 & 0 & )
  \end{array}
\end{align*}
$$

#### 行列にする

$$
\begin{align*}
	S &=
	\left(
	\begin{array}{cccc}
		0 & 0 & 0 & 0\\\\
		0 & 1 & 0 & -1\\\\
		0 & 0 & 0 & 0\\\\
		0 & -1 & 0 & 1
	\end{array}
	\right)\\\\[10pt]
	C &=
	\left(
	\begin{array}{cccc}
		1 & 1 & 1 & 1\\\\
		1 & 0 & -1 & 0\\\\
		1 & -1 & 1 & -1\\\\
		1 & 0 & -1 & 0
	\end{array}
	\right)
\end{align*}
$$

#### sin,cos の 2 つの周波数成分に分解

離散フーリエ変換（DFT）の前段階

入力ベクトルを $sin, cos$ の周波数成分にそれぞれ変換する。

$$
\begin{align*}
	F_C &= CX_{in}\\\\
	F_S &= SX_{in}
\end{align*}
$$

#### 二つの周波数成分からもとのベクトルを合成

逆離散フーリエ変換（IDFT）の前段階

$sin,cos$ の周波数成分から元のベクトルを合成する。

$$
\begin{align*}
	X_{out} = \frac{CF_C + SF_S}{N}
\end{align*}
$$

※定義より、もとまった係数とサンプリングした三角関数ベクトルの積を合わせるともとのベクトルが再現できる

### 複素数形式で表示

$W=C+iS$ とおいて新しい行列を考えると、

$$
W =
	\left(
	\begin{array}{cccc}
		1 & 1 & 1 & 1\\\\
		1 & i & -1 & -i\\\\
		1 & -1 & 1 & -1\\\\
		1 & -i & -1 & i
	\end{array}
	\right)
$$

となる。

> オイラーの公式
>
> $$
> e^{i\theta} = \cos\theta + i\sin\theta
> $$

を用いて、先ほどの $W$ を書き直すと、

$$
W =
	\left(
	\begin{array}{cccc}
		1 & 1 & 1 & 1\\\\
		1 & e^{2i\pi/4} & e^{4i\pi/4} & e^{6i\pi/4}\\\\
		1 & e^{4i\pi/4} & e^{8i\pi/4} & e^{12i\pi/4}\\\\
		1 & e^{6i\pi/4} & e^{12i\pi/4} & e^{18i\pi/4}
	\end{array}
	\right)
$$

### 離散フーリエ変換（DFT）

$W$ に対して、入力ベクトル $X_{in}$ を作用させると、フーリエ変換後の複素ベクトルが得られる。

$$
F = W X_{in}
$$

### 逆離散フーリエ変換（IDFT)

$\overline{W}=C-iS$ とおく。

$$
\begin{align*}
	X_{out} &= F_C + iF_S\\\\
	F_C &= CX_{in}\\\\
	iF_S &= (iS)X_{in}
\end{align*}
$$

より、

$$
\begin{align*}
	X_{out} = \frac{CF_C + \frac{1}{i^2}(iS)(iF_S)}{N} = \frac{CF_C - (iS)(iF_S)}{N}
\end{align*}
$$

ここで、$SC=O$ であるので、

$CS = SC = O$ の $N=4$ での検算．

```python
from sympy import *

C = Matrix(
    [[1,1,1,1],
     [1,0,-1,0],
     [1,-1,1,-1],
     [1,0,-1,0]]
)

S = Matrix(
    [[0,0,0,0],
    [0,1,0,-1],
    [0,0,0,0],
    [0,-1,0,1]]
)

print(C @ S)
```

↓ 出力

```
Matrix([
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0]])
```

$$
\begin{align*}
	X_{out} &= \frac{CF_C - (iS)(iF_S) - iSF_C + iCF_S}{N}\\\\[5pt]
	&= \frac{(C - iS)(F_C + iF_S)}{N}
\end{align*}
$$

$F = F_C + iF_S$ とおくと、

$$
\begin{align*}
	X_{out} = \frac{\overline{W}F}{N}
\end{align*}
$$

以上より、

$$
\begin{align*}
	\text{DFT:}\quad
	&F = WX_{in}\\\\[5pt]
	\text{IDFT:}\quad
	&X_{out} = \frac{1}{N} \overline{W} F
\end{align*}
$$

が得られる。

## 公式

### 離散フーリエ変換

$W$ の要素（回転因子） が、

$$
\begin{align*}
	W_{k,n} = e^{2\pi ik\frac{n}{N}}
\end{align*}
$$

と表されることを用いて、

$$
F = WX = \sum_{k=0}^{N-1}X[k]\~ e^{2i\pi k\frac{n}{N}}
$$

### 逆離散フーリエ変換

$\overline{W}$ は

$$
\begin{align*}
	e^{-i\theta} &= \cos(-\theta) + i\sin(-\theta)\\\\
	&= \cos\theta - i\sin\theta
\end{align*}
$$

であることを用いて、

$$
\begin{align*}
	W_{k,n} = e^{-2\pi kn\frac{n}{N}}
\end{align*}
$$

よって、

$$
X = \frac{1}{N}\sum_{n=0}^{N-1} F[n]\~ e^{-2i\pi k\frac{n}{N}}
$$

普通のフーリエ変換の公式

$$
\hat{f}(\xi) = \int_{-\infty}^{\infty} f(x)e^{-2\pi ix\xi} dx
$$

にならって、

$$
\begin{align*}
	\text{DFT:}\quad
	&F = \sum_{k=0}^{N-1}X[k]\~ e^{-2i\pi k\frac{n}{N}}\\\\[5pt]
	\text{IDFT:}\quad
	&X = \frac{1}{N}\sum_{n=0}^{N-1} F[n]\~ e^{2i\pi k\frac{n}{N}}
\end{align*}
$$

と表記する場合もある。
**↑ 以降はこの表記を使います！**

**いよいよ高速化です！**
