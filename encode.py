import argparse
import numpy as np
import re


def parse_vector(v, dims=None):
    vec = np.array(list(map(int, re.findall(r"-?\d+", v))))
    if dims is not None:
        assert len(vec) == dims, f"Dimension mismatch: expected {dims}, got {len(vec)}"
    return vec


def parse_ldt(file):
    
    with open(file, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    name = ""
    desc = ""
    points = {}
    splits = {}
    ldtree = {}

    i = 0
    while i < len(lines):
        line = lines[i]

        # ---- NAME ----
        if line.startswith("PROBLEM"):
            name = line.split(maxsplit=2)[2]
        
        # ---- DESCRIPTION ----
        elif line.startswith("DESCRIPTION"):
            desc = line.split(maxsplit=2)[2]

        # ---- POINTS ----
        if line.startswith("POINTS"):
            num_points, dim_points = map(int, line.split()[1:])
            for _ in range(num_points):
                i += 1
                idx, point = lines[i].split(maxsplit=1)
                points[int(idx)] = parse_vector(point, dim_points)

        # ---- SPLITS ----
        elif line.startswith("SPLITS"):
            num_splits, dim_splits = map(int, line.split()[1:])
            for _ in range(num_splits):
                i += 1
                idx, split = lines[i].split(maxsplit=1)
                splits[int(idx)] = parse_vector(split, dim_splits)

        # ---- LDTREE ----
        elif line.startswith("LDTREE"):
            num_nodes, _, _ = map(int, line.split()[1:])
            for _ in range(num_nodes):
                i += 1
                row = lines[i].split()
                idx = int(row[0])

                if row[1] == "LEAF":
                    val = int(re.findall(r"\{(\d+)\}", row[2])[0])
                    ldtree[idx] = ("LEAF", val)
                elif row[1] == "NODE":
                    val = int(row[2])
                    lt = int(re.search(r"LT:(\d+)", row[3]).group(1))
                    gt = int(re.search(r"GT:(\d+)", row[3]).group(1))
                    ldtree[idx] = ("NODE", val, lt, gt)

        i += 1

    assert dim_points == dim_splits, "Dimension mismatch"
    dims = dim_points

    return name, desc, dims, points, splits, ldtree


def encode_dot(split, var="c"):
    terms = []
    for i, v in enumerate(split):
        if v == 0:
            continue
        elif v == -1:
            terms.append(f" - {var}[{i}]")
        elif v == 1:
            terms.append(f" + {var}[{i}]")
        elif v > 0:
            terms.append(f" + {abs(v)} * {var}[{i}]")
        elif v < 0:
            terms.append(f" - {abs(v)} * {var}[{i}]")
        else:
            raise ValueError(f"Invalid split value: {v}")
    return "".join(terms) if terms else "0.0"


def encode_c(name, desc, dims, points, splits, ldtree):

    def build_node(node_id, indent=1):
        tab = "    " * indent
        node = ldtree[node_id]

        if node[0] == "LEAF":
            s = f"{tab}static int x[DIMS] = {{"
            s += ", ".join([f"{int(pi)}" for pi in points[node[1]]])
            s += "};\n"
            s += f"{tab}return x;\n"
            return s

        _, split_idx, lt, gt = node
        expr = encode_dot(splits[split_idx], var="c")

        s = f"{tab}if ({expr} < 0.0) {{\n"
        s += build_node(lt, indent + 1)
        s += f"{tab}}} else {{\n"
        s += build_node(gt, indent + 1)
        s += f"{tab}}}\n"

        return s

    code = []

    # ---- includes ----
    code.append("#include <stdio.h>\n")
    code.append("#include <stdlib.h>\n")
    code.append("#include <string.h>\n\n")

    code.append(f"#define DIMS {dims}\n\n")

    # ---- solver ----
    code.append("static inline const int *solve(double *c) {\n")
    code.append(build_node(0))
    code.append("}\n\n")

    # ---- CLI parsing ----
    code.append("int parse_cost(int argc, char **argv, double *c) {\n")
    code.append("    for (int i = 1; i < argc; ++i) {\n")
    code.append("        if ((strcmp(argv[i], \"-c\") == 0) || (strcmp(argv[i], \"--cost\") == 0)) {\n")
    code.append("            if (i + DIMS >= argc) {\n")
    code.append("                fprintf(stderr, \"Error: expected %d values after %s\\n\", DIMS, argv[i]);\n")
    code.append("                return 0;\n")
    code.append("            }\n")
    code.append("            for (int j = 0; j < DIMS; ++j) {\n")
    code.append("                c[j] = atof(argv[i + 1 + j]);\n")
    code.append("            }\n")
    code.append("            return 1;\n")
    code.append("        }\n")
    code.append("        if ((strcmp(argv[i], \"-h\") == 0) || (strcmp(argv[i], \"--help\") == 0)) {\n")
    code.append("            return -1;\n")
    code.append("        }\n")
    code.append("    }\n")
    code.append("    return 0;\n")
    code.append("}\n\n")

    # ---- help ----
    code.append("void print_help(const char *prog) {\n")
    code.append(f"    printf(\"{name}: {desc}\\n\\n\");\n")
    code.append("    printf(\"Usage: %s -c <c1> <c2> ... <c%d>\\n\", prog, DIMS);\n")
    code.append("    printf(\"\\nOptions:\\n\");\n")
    code.append("    printf(\"  -c, --cost    Cost vector (%d floats)\\n\", DIMS);\n")
    code.append("    printf(\"  -h, --help    Show this help message\\n\");\n")
    code.append("}\n\n")

    # ---- main ----
    code.append("int main(int argc, char **argv) {\n")
    code.append("    double c[DIMS];\n")

    code.append("    int status = parse_cost(argc, argv, c);\n\n")

    code.append("    if (status == -1) {\n")
    code.append("        print_help(argv[0]);\n")
    code.append("        return 0;\n")
    code.append("    }\n\n")

    code.append("    if (status == 0) {\n")
    code.append("        fprintf(stderr, \"Error: missing required argument -c / --cost\\n\");\n")
    code.append("        print_help(argv[0]);\n")
    code.append("        return 1;\n")
    code.append("    }\n\n")

    code.append("    const int *x = solve(c);\n\n")

    code.append("    printf(\"[\");\n")
    code.append("    for (int i = 0; i < DIMS; ++i) {\n")
    code.append("        printf(\"%d\", x[i]);\n")
    code.append("        if (i < DIMS - 1) printf(\", \");\n")
    code.append("    }\n")
    code.append("    printf(\"]\\n\");\n\n")

    code.append("    return 0;\n")
    code.append("}\n")

    return "".join(code)


def encode_numba(name, desc, dims, points, splits, ldtree):

    def build_node(node_id, indent=0):
        tab = "    " * indent
        node = ldtree[node_id]

        if node[0] == "LEAF":
            s = f"{tab}return ["
            s += ", ".join([f"{int(pi)}" for pi in points[node[1]]])
            s += "]\n"
            return s

        _, split_idx, lt, gt = node
        expr = encode_dot(splits[split_idx])

        s = f"{tab}if {expr} < 0.0:\n"
        s += build_node(lt, indent + 1)
        s += f"{tab}else:\n"
        s += build_node(gt, indent + 1)

        return s

    code = []

    code.append("import argparse\n")
    code.append("import numpy as np\n")
    code.append("from numba import njit\n")
    code.append("\n")
    code.append("\n")

    code.append(f"DIMS = {dims}\n")
    code.append("\n")
    code.append("\n")

    code.append("@njit\n")
    code.append("def solve(c):\n")
    code.append(build_node(0, indent=1))
    code.append("\n")
    code.append("\n")

    code.append(f"parser = argparse.ArgumentParser(description='{name}: {desc}')\n")
    code.append("parser.add_argument('-c', '--cost', type=float, nargs=DIMS, required=True)\n")
    code.append("args = parser.parse_args()\n")
    code.append("\n")

    code.append("c = np.asarray(args.cost, dtype=np.float64)\n")
    code.append("x = solve(c)\n")
    code.append("print(x)\n")

    return "".join(code)


def encode_python(name, desc, dims, points, splits, ldtree):

    def build_node(node_id, indent=0):
        tab = "    " * indent
        node = ldtree[node_id]

        if node[0] == "LEAF":
            s = f"{tab}return ["
            s += ", ".join([f"{int(pi)}" for pi in points[node[1]]])
            s += "]\n"
            return s

        _, split_idx, lt, gt = node
        expr = encode_dot(splits[split_idx])

        s = f"{tab}if {expr} < 0.0:\n"
        s += build_node(lt, indent + 1)
        s += f"{tab}else:\n"
        s += build_node(gt, indent + 1)

        return s

    code = []

    code.append("import argparse\n")
    code.append("import numpy as np\n")
    code.append("\n")
    code.append("\n")

    code.append(f"DIMS = {dims}\n")
    code.append("\n")
    code.append("\n")

    code.append("def solve(c):\n")
    code.append(build_node(0, indent=1))
    code.append("\n")
    code.append("\n")

    code.append(f"parser = argparse.ArgumentParser(description='{name}: {desc}')\n")
    code.append("parser.add_argument('-c', '--cost', type=float, nargs=DIMS, required=True)\n")
    code.append("args = parser.parse_args()\n")
    code.append("\n")

    code.append("c = np.asarray(args.cost, dtype=np.float64)\n")
    code.append("x = solve(c)\n")
    code.append("print(x)\n")

    return "".join(code)


parser = argparse.ArgumentParser(description='Encoder for .ldt files')
parser.add_argument('file', type=str, help='The .ldt file to encode')
parser.add_argument('--format', '-f', type=str, required=True, choices=['c', 'python', 'numba'], help='The output format')
parser.add_argument('--output', '-o', type=str, required=True, help='The output file name')


if __name__ == '__main__':
    args = parser.parse_args()

    with open(args.file, 'r') as input_stream:

        name, desc, dims, points, splits, ldtree = parse_ldt(args.file)

        if args.format == 'c':
            output_stream = encode_c(name, desc, dims, points, splits, ldtree)
        elif args.format == 'numba':
            output_stream = encode_numba(name, desc, dims, points, splits, ldtree)
        elif args.format == 'python':
            output_stream = encode_python(name, desc, dims, points, splits, ldtree)
        else:
            raise ValueError(f"Unsupported format: {args.format}")

    with open(args.output, 'w') as output_file:
        output_file.write(output_stream)
