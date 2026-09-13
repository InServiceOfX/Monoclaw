"""Exact arithmetic smoke checks for sage -python; JSON stdout for agents."""
import json
from sage.all import QQ, PolynomialRing, matrix
from sage.version import version

ring = PolynomialRing(QQ, 'x')
x = ring.gen()
assert (x**4 - 1) == (x - 1)*(x + 1)*(x**2 + 1)
A = matrix(QQ, [[1, 2], [3, 4]])
assert A.det() == -2
assert A * A.inverse() == matrix.identity(QQ, 2)
print(json.dumps({'passed': True, 'sage_version': version,
                  'factorization': str((x**4 - 1).factor()),
                  'determinant': str(A.det()), 'exact_inverse': True}))
