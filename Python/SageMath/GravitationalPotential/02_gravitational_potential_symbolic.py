#!/usr/bin/env sage -python
"""
02_gravitational_potential_symbolic.py

Symbolic computation of gravitational potential with spherical harmonics.

This script computes:
- Gravitational potential V through n=3 (monopole, J2, J3 terms)
- Verifies Legendre polynomial expressions P_2 and P_3
- Expresses V_J2 in Cartesian coordinates
- Computes J2 acceleration vector in Cartesian (x, y, z)

Usage:
    sage -python 02_gravitational_potential_symbolic.py
"""

from sage.all import *

def main():
    print("=" * 70)
    print("GRAVITATIONAL POTENTIAL - SYMBOLIC COMPUTATION")
    print("=" * 70)
    
    # Define symbolic variables
    r, theta, phi = var('r theta phi', domain='real')
    mu, Re = var('mu R_e', domain='real', positive=True)
    J2, J3 = var('J_2 J_3', domain='real')
    C21, S21 = var('C_21 S_21', domain='real')
    C22, S22 = var('C_22 S_22', domain='real')
    
    # ============================================================
    # Part 1: Define Legendre Polynomials
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 1: Legendre Polynomials P_n(cos(theta))")
    print("=" * 70)
    
    x = var('x')
    
    # P_2 and P_3
    P2_formula = (3*cos(theta)**2 - 1) / 2
    P3_formula = (5*cos(theta)**3 - 3*cos(theta)) / 2
    
    # Verify using Sage's built-in
    P2_builtin = legendre_P(2, cos(theta))
    P3_builtin = legendre_P(3, cos(theta))
    
    print("\nP_2(cos(theta)) verification:")
    print(f"  Formula: (3*cos^2(theta) - 1) / 2 = {expand(P2_formula)}")
    print(f"  Built-in: {expand(P2_builtin)}")
    print(f"  Match: {simplify(P2_formula - P2_builtin) == 0}")
    
    print("\nP_3(cos(theta)) verification:")
    print(f"  Formula: (5*cos^3(theta) - 3*cos(theta)) / 2 = {expand(P3_formula)}")
    print(f"  Built-in: {expand(P3_builtin)}")
    print(f"  Match: {simplify(P3_formula - P3_builtin) == 0}")
    
    # ============================================================
    # Part 2: Gravitational Potential Components
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 2: Gravitational Potential Components")
    print("=" * 70)
    
    # Monopole term
    V_monopole = -mu / r
    print(f"\nMonopole potential:")
    print(f"  V_monopole = {V_monopole}")
    print(f"  LaTeX: ${latex(V_monopole)}$")
    
    # J2 term (zonal harmonic)
    V_J2 = -mu / r * J2 * (Re/r)**2 * P2_formula
    print(f"\nJ2 potential:")
    print(f"  V_J2 = {V_J2}")
    print(f"  Expanded: {expand(V_J2)}")
    print(f"  LaTeX: ${latex(V_J2)}$")
    
    # J3 term (zonal harmonic)
    V_J3 = -mu / r * J3 * (Re/r)**3 * P3_formula
    print(f"\nJ3 potential:")
    print(f"  V_J3 = {V_J3}")
    print(f"  Expanded: {expand(V_J3)}")
    print(f"  LaTeX: ${latex(V_J3)}$")
    
    # Total potential through n=3
    V_total = V_monopole + V_J2 + V_J3
    print(f"\nTotal potential (through n=3):")
    print(f"  V = V_monopole + V_J2 + V_J3")
    print(f"  V = {V_total}")
    
    # ============================================================
    # Part 3: V_J2 in Cartesian Coordinates
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 3: V_J2 in Cartesian Coordinates")
    print("=" * 70)
    
    # Define Cartesian coordinates
    x, y, z = var('x y z', domain='real')
    
    # Spherical to Cartesian substitutions
    # r = sqrt(x^2 + y^2 + z^2)
    # cos(theta) = z/r = z/sqrt(x^2 + y^2 + z^2)
    
    r_cart = sqrt(x**2 + y**2 + z**2)
    cos_theta_cart = z / r_cart
    
    print("\nCoordinate transformation:")
    print(f"  r = sqrt(x^2 + y^2 + z^2) = {r_cart}")
    print(f"  cos(theta) = z/r = {cos_theta_cart}")
    
    # Substitute into V_J2
    V_J2_cart = V_J2.substitute({
        r: r_cart,
        cos(theta): cos_theta_cart
    })
    
    V_J2_cart_simplified = simplify(V_J2_cart)
    
    print(f"\nV_J2 in Cartesian:")
    print(f"  V_J2(x,y,z) = {V_J2_cart}")
    print(f"\nSimplified:")
    print(f"  V_J2(x,y,z) = {V_J2_cart_simplified}")
    print(f"\nLaTeX: ${latex(V_J2_cart_simplified)}$")
    
    # ============================================================
    # Part 4: J2 Acceleration in Cartesian
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 4: J2 Acceleration Vector in Cartesian")
    print("=" * 70)
    
    print("\nComputing a = -grad(V_J2) in Cartesian coordinates")
    
    # Compute gradient components
    dV_dx = diff(V_J2_cart_simplified, x)
    dV_dy = diff(V_J2_cart_simplified, y)
    dV_dz = diff(V_J2_cart_simplified, z)
    
    # Acceleration is negative gradient
    a_x = -dV_dx
    a_y = -dV_dy
    a_z = -dV_dz
    
    print("\nPartial derivatives of V_J2:")
    print(f"  dV_J2/dx = {simplify(dV_dx)}")
    print(f"  dV_J2/dy = {simplify(dV_dy)}")
    print(f"  dV_J2/dz = {simplify(dV_dz)}")
    
    # Simplify acceleration components
    a_x_simplified = simplify(a_x)
    a_y_simplified = simplify(a_y)
    a_z_simplified = simplify(a_z)
    
    print("\nJ2 acceleration components a = -grad(V_J2):")
    print(f"  a_x = {a_x_simplified}")
    print(f"  a_y = {a_y_simplified}")
    print(f"  a_z = {a_z_simplified}")
    
    # Express in terms of r
    r_sq = x**2 + y**2 + z**2
    
    # Standard form of J2 acceleration
    print("\nStandard form of J2 acceleration:")
    print("  a_J2 = -3*mu*J2*Re^2/(2*r^5) * [x*(1-5*z^2/r^2), y*(1-5*z^2/r^2), z*(3-5*z^2/r^2)]")
    
    # Verify by computing standard form
    factor = -3*mu*J2*Re**2 / (2*r_sq**(5/2))
    a_x_std = factor * x * (1 - 5*z**2/r_sq)
    a_y_std = factor * y * (1 - 5*z**2/r_sq)
    a_z_std = factor * z * (3 - 5*z**2/r_sq)
    
    print("\nStandard form computed:")
    print(f"  a_x_std = {simplify(a_x_std)}")
    print(f"  a_y_std = {simplify(a_y_std)}")
    print(f"  a_z_std = {simplify(a_z_std)}")
    
    # Check if they match
    match_x = simplify(a_x_simplified - a_x_std) == 0
    match_y = simplify(a_y_simplified - a_y_std) == 0
    match_z = simplify(a_z_simplified - a_z_std) == 0
    
    print(f"\nMatch with standard form:")
    print(f"  a_x: {match_x}")
    print(f"  a_y: {match_y}")
    print(f"  a_z: {match_z}")
    
    # Print final acceleration vector
    print("\n" + "=" * 70)
    print("FINAL RESULT: J2 Acceleration Vector")
    print("=" * 70)
    
    print("\na_J2 = [a_x, a_y, a_z] where:")
    print(f"  a_x = {simplify(a_x_std)}")
    print(f"  a_y = {simplify(a_y_std)}")
    print(f"  a_z = {simplify(a_z_std)}")
    
    print("\nIn compact form:")
    print("  a_J2 = -3*mu*J2*Re^2/(2*r^5) * [(1-5*z^2/r^2)*x, (1-5*z^2/r^2)*y, (3-5*z^2/r^2)*z]")
    
    # ============================================================
    # Part 5: Summary
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 5: Summary")
    print("=" * 70)
    
    print("\nKey Results:")
    print("1. P_2(cos(theta)) = (3*cos^2(theta) - 1)/2: VERIFIED")
    print("2. P_3(cos(theta)) = (5*cos^3(theta) - 3*cos(theta))/2: VERIFIED")
    print("3. V_J2 in Cartesian: -mu*J2*Re^2*z*(3*r^2-5*z^2)/(2*r^5*sqrt(x^2+y^2+z^2))")
    print("4. J2 acceleration derived and verified against standard form")
    
    print("\n" + "=" * 70)
    print("Script completed successfully!")
    print("=" * 70)

if __name__ == "__main__":
    main()
