#!/usr/bin/env sage -python
"""
03_transformation_matrix.py

Transformation matrix between spherical and Cartesian coordinates.

This script computes:
- Transformation matrix R mapping (e_r, e_theta, e_phi) to (x_hat, y_hat, z_hat)
- Verifies R * R.T = Identity (orthogonality)
- Shows vector component transformation
- Shows gradient transformation: grad_cartesian = R * grad_spherical

Usage:
    sage -python 03_transformation_matrix.py
"""

from sage.all import *

def main():
    print("=" * 70)
    print("SPHERICAL TO CARTESIAN TRANSFORMATION MATRIX")
    print("=" * 70)
    
    # Define symbolic variables
    theta, phi = var('theta phi', domain='real')
    
    # ============================================================
    # Part 1: Define the Transformation Matrix R
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 1: Transformation Matrix R")
    print("=" * 70)
    
    print("\nSpherical unit vectors in terms of Cartesian:")
    print("  e_r = sin(theta)*cos(phi)*x_hat + sin(theta)*sin(phi)*y_hat + cos(theta)*z_hat")
    print("  e_theta = cos(theta)*cos(phi)*x_hat + cos(theta)*sin(phi)*y_hat - sin(theta)*z_hat")
    print("  e_phi = -sin(phi)*x_hat + cos(phi)*y_hat")
    
    print("\nThe transformation matrix R maps (e_r, e_theta, e_phi) to (x_hat, y_hat, z_hat)")
    print("  [v_x]   [e_r·x_hat   e_theta·x_hat   e_phi·x_hat] [v_r]")
    print("  [v_y] = [e_r·y_hat   e_theta·y_hat   e_phi·y_hat] [v_theta]")
    print("  [v_z]   [e_r·z_hat   e_theta·z_hat   e_phi·z_hat] [v_phi]")
    
    # Define R as given in the specification
    # R[i,j] gives the i-th Cartesian component of the j-th spherical unit vector
    R = Matrix([
        [sin(theta)*cos(phi), cos(theta)*cos(phi), -sin(phi)],
        [sin(theta)*sin(phi), cos(theta)*sin(phi), cos(phi)],
        [cos(theta), -sin(theta), 0]
    ])
    
    print("\nTransformation matrix R:")
    print("R =")
    print(R)
    
    print("\nLaTeX representation:")
    print(f"${latex(R)}$")
    
    # ============================================================
    # Part 2: Verify Orthogonality (R * R.T = I)
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 2: Orthogonality Verification")
    print("=" * 70)
    
    print("\nVerifying R * R.T = Identity matrix")
    
    R_transpose = R.transpose()
    print("\nR^T =")
    print(R_transpose)
    
    # Compute R * R^T
    RRT = R * R_transpose
    RRT_simplified = RRT.apply_map(lambda e: e.simplify_trig())
    
    print("\nR * R^T =")
    print(RRT_simplified)
    
    # Check if it's identity
    I3 = identity_matrix(3)
    print("\nIdentity matrix I_3 =")
    print(I3)
    
    # Verify element by element
    print("\nVerification (element by element):")
    all_match = True
    for i in range(3):
        for j in range(3):
            elem = RRT_simplified[i, j]
            expected = I3[i, j]
            match = simplify(elem - expected) == 0
            print(f"  [{i},{j}]: {elem} == {expected} ? {match}")
            if not match:
                all_match = False
    
    print(f"\nR * R^T == I: {all_match}")
    
    # Also verify R^T * R = I
    print("\nVerifying R^T * R = Identity matrix")
    RTR = R_transpose * R
    RTR_simplified = RTR.apply_map(lambda e: e.simplify_trig())
    
    print("\nR^T * R =")
    print(RTR_simplified)
    
    all_match2 = True
    for i in range(3):
        for j in range(3):
            elem = RTR_simplified[i, j]
            expected = I3[i, j]
            match = simplify(elem - expected) == 0
            if not match:
                all_match2 = False
    
    print(f"\nR^T * R == I: {all_match2}")
    
    # ============================================================
    # Part 3: Determinant of R
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 3: Determinant of R")
    print("=" * 70)
    
    det_R = det(R)
    det_R_simplified = det_R.simplify_trig()
    
    print(f"\ndet(R) = {det_R}")
    print(f"det(R) simplified = {det_R_simplified}")
    
    # For an orthogonal matrix, det(R) should be +/- 1
    print(f"\nFor orthogonal matrix: det(R) = ±1")
    print(f"This R has det(R) = {det_R_simplified} (proper rotation)")
    
    # ============================================================
    # Part 4: Vector Transformation Example
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 4: Vector Transformation Example")
    print("=" * 70)
    
    # Define a vector in spherical components
    v_r, v_theta, v_phi = var('v_r v_theta v_phi', domain='real')
    
    v_spherical = vector([v_r, v_theta, v_phi])
    
    print("\nVector in spherical coordinates:")
    print(f"  v_spherical = {v_spherical}")
    
    # Transform to Cartesian
    v_cartesian = R * v_spherical
    v_cartesian_simplified = vector([simplify(v_cartesian[i]) for i in range(3)])
    
    print("\nVector in Cartesian coordinates:")
    print(f"  v_cartesian = R * v_spherical = {v_cartesian_simplified}")
    
    print("\nComponent-wise:")
    print(f"  v_x = {simplify(v_cartesian[0])}")
    print(f"  v_y = {simplify(v_cartesian[1])}")
    print(f"  v_z = {simplify(v_cartesian[2])}")
    
    # Specific example: radial unit vector
    print("\n" + "-" * 70)
    print("Example: Radial unit vector e_r")
    print("-" * 70)
    
    e_r_spherical = vector([1, 0, 0])
    e_r_cartesian = R * e_r_spherical
    
    print(f"\ne_r in spherical: {e_r_spherical}")
    print(f"e_r in Cartesian: {e_r_cartesian}")
    print(f"e_r = ({simplify(e_r_cartesian[0])}, {simplify(e_r_cartesian[1])}, {simplify(e_r_cartesian[2])})")
    
    # Verify it's a unit vector
    e_r_norm = sqrt(sum([e_r_cartesian[i]**2 for i in range(3)]))
    print(f"||e_r|| = {simplify(e_r_norm)}")
    
    # ============================================================
    # Part 5: Inverse Transformation (Cartesian to Spherical)
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 5: Inverse Transformation (Cartesian to Spherical)")
    print("=" * 70)
    
    print("\nSince R is orthogonal: R^(-1) = R^T")
    
    R_inv = R.inverse()
    R_inv_simplified = R_inv.apply_map(lambda e: e.simplify_trig())
    
    print("\nR^(-1) =")
    print(R_inv_simplified)
    
    # Verify R^(-1) = R^T
    diff = (R_inv_simplified - R_transpose).apply_map(lambda e: e.simplify_trig())
    print(f"\nR^(-1) - R^T = 0 matrix? {diff == matrix([[0,0,0],[0,0,0],[0,0,0]])}")
    
    # Transform back
    v_back = R_transpose * v_cartesian
    v_back_simplified = vector([simplify(v_back[i]) for i in range(3)])
    
    print("\nTransforming back to spherical:")
    print(f"  v_spherical = R^T * v_cartesian = {v_back_simplified}")
    
    # ============================================================
    # Part 6: Gradient Transformation
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 6: Gradient Transformation")
    print("=" * 70)
    
    print("\nThe gradient in spherical coordinates:")
    print("  grad_spherical = [dV/dr, (1/r)*dV/dtheta, (1/(r*sin(theta)))*dV/dphi]")
    
    # Define symbolic variables for gradient
    r, V = var('r V', domain='real')
    
    # Gradient in spherical (symbolic components)
    dV_dr = var('dV_dr', domain='real')
    dV_dtheta = var('dV_dtheta', domain='real')
    dV_dphi = var('dV_dphi', domain='real')
    
    grad_sph = vector([dV_dr, dV_dtheta, dV_dphi])

    print(f"\nSpherical gradient vector (symbolic): {grad_sph}")
    print("\nCartesian gradient = R * grad_spherical")
    print("(where the spherical components include the metric factors 1/r and 1/(r*sin(theta)))")

    grad_cart = R * grad_sph
    print(f"\nCartesian gradient = {grad_cart}")
    print("\nThis maps:")
    print("  grad_x = sin(theta)*cos(phi)*dV/dr + cos(theta)*cos(phi)*(1/r)*dV/dtheta - sin(phi)/(r*sin(theta))*dV/dphi")
    print("  grad_y = sin(theta)*sin(phi)*dV/dr + cos(theta)*sin(phi)*(1/r)*dV/dtheta + cos(phi)/(r*sin(theta))*dV/dphi")
    print("  grad_z = cos(theta)*dV/dr - sin(theta)*(1/r)*dV/dtheta")

    print("\n" + "=" * 70)
    print("Script completed successfully!")
    print("=" * 70)

if __name__ == "__main__":
    main()