# Integer Linear Programming Oracles

This repository contains oracles for solving integer linear programs of the form

$$\begin{array}{ll}\max & \mathbf{c}^{\top}\mathbf{x} \\ \text{s.t.} & \mathbf{x} \in X\end{array}$$

that are constructed once for a fixed feasible set $X \subseteq \mathbb{Z}^n$, and can be queried efficiently to retrieve the optimal solution corresponding to any cost vector $\mathbf{c} \in \mathbb{R}^n$. They can be helpful in online settings where such problems need to be solved repeatedly for a large number of different cost vectors, allowing to avoid the overhead of solving each instance from scratch. This repository aims at sharing already-built oracles in a unified format, making it easier for practitioners to find and use them for their specific problems. 

Feel free to contribute with your own oracles by opening a [pull request](https://github.com/TheoGuyard/ilp-oracles/pulls).
Any feedback or contribution is welcome.

## Quickstart

Oracles are stored in `.ilp` files. They can be encoded to be used in practice using the `encode.py` script as follows:

```bash
python encode.py <file.ilp> -f <format> -o <output> 
```

The `-f` flag indicates the output code format, which can be either `python`, `numba`, or `c`. The `-o` flag indicates the output file name. The generated file can then be used by inputting the cost vector coefficients as command line arguments. With `python` and `numba` formats, the output file can be run as follows:

```bash
python output.py 1.53 -0.41 0.87 ...
```

With the `c` format, the output file must be compiled first, and then can be run as follows:

```bash
gcc output.c -o output
./output 1.53 -0.41 0.87 ...
```

## Available oracles

The repository currently contains oracles for the following problems:

| Oracle file | Description | Cost vector format |
|---|---|---|
| `cut-d.ilp` | Minimum weighted cut problem on undirected graph with `d` vertices. | The cost vector encodes the edge weights as `c = [c_{1,2},c_{1,3},...,c_{d-1,d}]` where `c_{i,j}=weight(i,j)`. Use `c_{i,j} = +infty` if no edge exists between vertices `i` and `j`.  
| `knp-d.ilp` | Knapsack problem with `d` items of increasing weights `w = [1,2,...,d]` and maximum capacity `W=d`. | The cost vector encodes the items value as `c = [c_{1},c_{2},...,c_{d}]` where `c_{i}=value(i)`. |
| `tsp-d.ilp` | Traveling salesman problem on undirected graph with `d` cities. | The cost vector encodes the cities distances as `c = [c_{1,2},c_{1,3},...,c_{d-1,d}]` where `c_{i,j}=-dist(i,j)`. Use `c_{i,j} = -infty` if no edge exists between cities `i` and `j`. |

## Oracle formats

Oracles currently available in the repository correspond to **linear decision trees**, traversed using any cost vector as input until a leaf returning the corresponding optimal solution is reached. They are stored in a unified `.ilp` file with the following sections.

**Header section**: Contains general information about the problem and the oracle.

```
PROBLEM     : <problem identifier>
DESCRIPTION : <problem description>
ORACLE      : <oracle type>
```

The `ORACLE` field indicates whether the decision tree oracle is proven to achieve the minimum depth possible for the given problem, that is, if is ensures an optimal worst-case complexity during queries.

**Points section**: Contains the list of points in the feasible set $X \subseteq \mathbb{Z}^n$.

```
POINTS <points number> <points dimension>
0 [0,1,1,...]
1 [1,0,0,...]
...
```

**Splits section**: Contains the list of splits used to branch in the decision tree.

```
SPLITS <splits number> <split dimension>
0 [-1,0,1,...]
1 [0,1,-1,...]
...
```

**Tree section**: Contains the structure of the decision tree, where each row is either a `LEAF` indicating the index of the corresponding problem solution when reached, or a `NODE` indicating the index of the split $\mathbf{s} \in \mathbb{Z}^n$ to be used for branching, and the index of the child node to be followed (`LT` if $\mathbf{s}^{\top}\mathbf{c} < 0$, `GT` if $\mathbf{s}^{\top}\mathbf{c} > 0$).
```
LDTREE <tree size> <tree depth> <tree width>
0 NODE 0 {LT:1,GT:2}
1 LEAF {1}
2 NODE 3 {LT:4,GT:5}
...
```

## Cite and License

`ilp-oracles` is distributed under
[MIT license](https://github.com/TheoGuyard/ilp-oracles/blob/main/LICENSE). Please cite the repository as follows:

> [Citation to be added soon] 
