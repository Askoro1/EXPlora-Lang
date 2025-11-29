import csv

from ..ast_nodes import *
from ..interpreter.utils import RuntimeValue


# ----------------------------
# Convert CSV cell → PrimitiveLiteral(int or float)
# ----------------------------
def numeric_literal(cell: str):
    cell = cell.strip()
    if cell == "":
        return PrimitiveLiteral(0)  # or raise error if desired

    try:
        iv = int(cell)
        return PrimitiveLiteral(iv)
    except ValueError:
        return PrimitiveLiteral(float(cell))


# ==================================================
#                  CSV READER
# ==================================================
def csv_reader_native(path_expr):
    """
    Called from EXPlora-Lang:
        csv_reader("file.csv")

    Returns:
        ArrayLiteral([
            ArrayLiteral([PrimitiveLiteral, PrimitiveLiteral, ...]),
            ...
        ])
    """
    path = path_expr[0].value
    assert isinstance(path, str), "csv_reader expects string literal path"

    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for raw_row in reader:
            row_literals = [int(cell) for cell in raw_row]
            rows.append(row_literals)

    shape = (len(rows), len(rows[0]))

    return RuntimeValue(rows, static_type=Type(base_type=PrimitiveType("int"),
                                                    dimension=2),
                                                    shape=shape)


# ==================================================
#                  CSV WRITER
# ==================================================
def csv_writer_native(path_expr, array_expr):
    """
    Called from EXPlora-Lang:
        csv_writer("out.csv", someArray)

    someArray must be an ArrayLiteral of ArrayLiteral of PrimitiveLiteral
    """
    assert isinstance(path_expr, StringLiteral), "csv_writer expects string literal path"
    assert isinstance(array_expr, ArrayLiteral), "csv_writer expects array of arrays"

    path = path_expr.value
    table = array_expr.value  # list[Expression] (here list[ArrayLiteral])

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        for row_expr in table:
            if not isinstance(row_expr, ArrayLiteral):
                raise TypeError("CSV writer expects an array of arrays")

            csv_row = []
            for cell_expr in row_expr.value:
                if not isinstance(cell_expr, PrimitiveLiteral):
                    raise TypeError("CSV cells must be numeric PrimitiveLiteral")
                csv_row.append(cell_expr.value)

            writer.writerow(csv_row)

    # No meaningful return → produce unit literal
    return PrimitiveLiteral(0)  # your language uses "unit"; replace with unit if defined