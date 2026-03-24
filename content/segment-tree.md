+++
title = "セグメントツリー"
date = "2022-07-02"
description = "セグ木をPythonで実装する"
[taxonomies]
category = ["競プロ"]
tags = ["アルゴリズム", "データ構造", "Python"]
[extra]
comment = true
+++

### 参考

[【木マスター養成講座】4-2. Segment 木ってなに〜？なんかうまく区間取ってくる編](https://www.youtube.com/watch?v=ReGvflPU81c&list=PL3Hpv03CoZ24p5a6qT0LsFKEhiDWxf_B_&index=4)

### RangeSumQuery

#### 方針

区間を完全 2 分木で管理する

```
|               27              |
|       11      |       16      |
|   6   |   5   |   11  |   5   |
| 1 | 5 | 2 | 3 | 2 | 9 | 5 | 0 |
```

$\downarrow$

```python
[27, 11, 16, 6, 5, 11, 5, 1, 5, 2, 3, 2, 9, 5, 0]
```

インデックスを割り当てる

```
|               27              |
[1]                             [2]
|       11      |       16      |
[2]             [3]             [4]
|   6   |   5   |   11  |   5   |
[4]     [5]     [6]     [7]     [8]
| 1 | 5 | 2 | 3 | 2 | 9 | 5 | 0 |
[8] [9] [10][11][12][13][14][15][16]
```

総和を取得する流れ

1. $l$ について、$l$ が偶数なら上に（$2$ で割る）、奇数なら右へ
2. $r$ について、$r$ が偶数なら上に（$2$ で割る）、奇数なら左へ

#### 実装

```python
class SegTree:
    def __init__(self, n, arr=None):
        self.seg_len = self.get_seglen(n)
        self.arr = [0] * self.seg_len * 2

        if arr:
            for i, v in enumerate(arr):
                self.add(i, v)

    def add(self, i, val):
        i += self.seg_len
        self.arr[i] += val
        while True:
            i >>= 1
            if i == 0:
                break
            self.arr[i] = self.arr[i*2] + self.arr[i*2+1]

    def sum(self, l, r):
        l += self.seg_len
        r += self.seg_len
        ans = 0
        while l < r:
            if l & 1:
                ans += self.arr[l]
                l += 1
            l >>= 1
            if r & 1:
                ans += self.arr[r-1]
                r -= 1
            r >>= 1
        return ans

    @staticmethod
    def get_seglen(n):
        log2_n = 0
        while n:
            log2_n += 1
            n >>= 1
        return 1 << log2_n
```
