+++
title = "Fenwick木（BIT）"
date = "2022-07-02"
description = "BITをPythonで実装する"
[taxonomies]
category = ["競プロ"]
tags = ["アルゴリズム", "データ構造", "Python"]
[extra]
comment = true
+++

# Fewnick Tree

BinaryIndexedTree(BIT) とも呼ばれるデータ構造です。要素の更新と区間の和を行うクエリを高速に処理できます。

## BIT の実装

構造

```
|---------------------------------------|
|-------------------|                   |
|---------|         |---------|         |
|----|    |----|    |----|    |----|    |
|  1 |  2 |  3 |  4 |  5 |  6 |  7 |  8 |
|0001|0010|0011|0100|0101|0110|0111|1000|
```

### 区間和を求める

$\rightarrow$ 0 になるまで LSB を減算しながら足す

#### 例)

- 配列 $a = [5, 3, 7, 9, 6, 4, 1, 2]$
- クエリ: $\sum_{i=1}^{7} a_i$

```
|               37              |
|       24      |               |
|   8   |       |   10  |       |
| 5 |(3)| 7 |(9)| 6 |(4)| 1 |(2)|
```

- $a_1 + a_2 + \dots + a_7$

| i   | 2 進表示 | 合計         |
| --- | -------- | ------------ |
| 7   | 0111     | 1 (0 + 1)    |
| 6   | 0110     | 11 (1 + 10)  |
| 4   | 0100     | 35 (11 + 24) |
| 0   | 0000     | 35           |

### 要素の更新

$a_i$ に $x$ を足す

$\rightarrow$ $i$ に LSB を加算しながら更新

#### 例)

- 配列 $a = [5, 3, 7, 9, 6, 4, 1, 2]$
- クエリ: $a_5$ に $2$ を足す

| i   | 2 進表示 |
| --- | -------- |
| 5   | 0101     |
| 6   | 0110     |
| 8   | 1000     |

```
|           37 → 39             |
|       24      |               |
|   8   |       | 10→12 |       |
| 5 |(3)| 7 |(9)|6→8|(4)| 1 |(2)|
```

## 最下位ビット

(LSB; Least Significant Bit)とも言う

2 進数で表したとき、もっとも小さい位をあらわす bit

- $01111100010$ の LSB は 2

### 求め方

2 の補数表現を利用すると、

```
-i <- ~i + 1
```

と表される。(~は bit 反転)

このとき、最下位ビットは

```
i & -i
```

として求められる。

```python
# BIT
class BIT:
    def __init__(self, n):
        self.size = n
        self.arr = [0] * (n + 1)

    def sum(self, i):
        s = 0
        while i:
            s += self.arr[i]
            i -= i & -i
        return s

    def add(self, i, x):
        while i <= self.size:
            self.arr[i] += x
            i += i & -i


# ----- query -----
bit = BIT(8)

bit.add(1, 5)
bit.add(2, 3)
bit.add(3, 7)
bit.add(4, 9)
bit.add(5, 6)
bit.add(6, 4)
bit.add(7, 1)
bit.add(8, 2)

print(bit.arr)

print(bit.sum(7))

bit.add(5, 2)

print(bit.sum(8))

##### OUT #####
5
20
0
[0, 5, 8, 7, 24, 6, 10, 1, 37]
35
39
```

## 区間の和を求める

- 累積和みたいに処理

```python
# BIT
class BIT:
    def __init__(self, n):
        self.size = n
        self.arr = [0] * (n + 1)

    def sum_1(self, i):
        s = 0
        while i:
            s += self.arr[i]
            i -= i & -i
        return s

    def sum(self, i, j):
        """[i, j) の和を求める"""
        return self.sum_1(j-1) - self.sum_1(i-1)

    def add(self, i, x):
        while i <= self.size:
            self.arr[i] += x
            i += i & -i

# ----- query -----
bit = BIT(8)

bit.add(1, 5)
bit.add(2, 3)
bit.add(3, 7)
bit.add(4, 9)
bit.add(5, 6)
bit.add(6, 4)
bit.add(7, 1)
bit.add(8, 2)

print(bit.sum(1, 2))
print(bit.sum(4, 8))
print(bit.sum(1, 1))

##### OUT #####
5
20
0
```

## 参考

- [BinaryIndexedTree - 北海道大学競技プログラミングサークル](https://www.slideshare.net/hcpc_hokudai/binary-indexed-tree)
- [Binary Indexed Tree（Fenwick Tree） - いかたこのたこつぼ](https://ikatakos.com/pot/programming_algorithm/data_structure/binary_indexed_tree)
