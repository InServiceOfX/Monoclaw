#!/usr/bin/env sage -python
"""
05_spherical_harmonics_visualization.py

Real spherical harmonics computation and visualization.

This script computes:
- Real spherical harmonics Y_lm for l = 0, 1, 2, 3
- Verifies Y_20 ~ (3cos^2(theta) - 1), Y_22 ~ sin^2(theta)*cos(2*phi), etc.
- Normalization: integral of Y_lm^2 over sphere = 1
- Orthogonality: integral of Y_lm * Y_l'm' over sphere = delta_ll' * delta_mm'

Usage:
    sage -python 05_spherical_harmonics_visualization.py
"""

from sage.all import *

def spherical_harmonic_real(l, m, theta, phi):
    """
    Compute real spherical harmonic Y_lm(theta, phi).
    
    Real spherical harmonics are defined as:
    - For m = 0: Y_l0 = N_l0 * P_l(cos(theta))
    - For m > 0: Y_lm = N_lm * P_lm(cos(theta)) * cos(m*phi)
    - For m < 0: Y_l|m| = N_l|m| * P_l|m|(cos(theta)) * sin(|m|*phi)
    
    where N_lm is the normalization constant.
    """
    # Normalization constant
    # N_lm = sqrt((2*l + 1)/(4*pi) * (l - |m|)! / (l + |m|)!)
    abs_m = abs(m)
    
    # Compute factorial ratio
    if l >= abs_m:
        factorial_ratio = factorial(l - abs_m) / factorial(l + abs_m)
    else:
        return 0
    
    N_lm = sqrt((2*l + 1) / (4*pi) * factorial_ratio)
    
    # Associated Legendre function
    P_lm = gen_legendre_P(l, abs_m, cos(theta))
    
    # Real spherical harmonic
    if m > 0:
        Y_lm = N_lm * P_lm * cos(m * phi)
    elif m < 0:
        Y_lm = N_lm * P_lm * sin(abs_m * phi)
    else:  # m == 0
        Y_lm = N_lm * P_lm
    
    return simplify(Y_lm)

def main():
    print("=" * 70)
    print("SPHERICAL HARMONICS - REAL FORM")
    print("=" * 70)
    
    # Define symbolic variables
    theta, phi = var('theta phi', domain='real')
    
    # ============================================================
    # Part 1: Compute Y_lm for l = 0, 1, 2, 3
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 1: Real Spherical Harmonics Y_lm(theta, phi)")
    print("=" * 70)
    
    # List of (l, m) pairs to compute
    lm_pairs = [
        (0, 0),
        (1, 0), (1, 1), (1, -1),
        (2, 0), (2, 1), (2, -1), (2, 2), (2, -2),
        (3, 0), (3, 1), (3, -1), (3, 2), (3, -2), (3, 3), (3, -3)
    ]
    
    harmonics = {}
    
    for l, m in lm_pairs:
        Y_lm = spherical_harmonic_real(l, m, theta, phi)
        harmonics[(l, m)] = Y_lm
        
        print(f"\nY_{l},{m}(theta, phi) = {Y_lm}")
        print(f"LaTeX: ${latex(Y_lm)}$")
    
    # ============================================================
    # Part 2: Verify Specific Forms
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 2: Verification of Specific Forms")
    print("=" * 70)
    
    # Y_20 should be proportional to (3*cos^2(theta) - 1)
    print("\nY_20 verification:")
    Y_20 = harmonics[(2, 0)]
    print(f"  Y_20 = {Y_20}")
    
    # Expected form: sqrt(5/(16*pi)) * (3*cos^2(theta) - 1)
    expected_Y20_coeff = sqrt(5 / (16*pi))
    expected_Y20 = expected_Y20_coeff * (3*cos(theta)**2 - 1)
    print(f"  Expected: sqrt(5/(16*pi)) * (3*cos^2(theta) - 1) = {expected_Y20}")
    print(f"  Match: {simplify(Y_20 - expected_Y20) == 0}")
    
    # Y_22 should be proportional to sin^2(theta) * cos(2*phi)
    print("\nY_22 verification:")
    Y_22 = harmonics[(2, 2)]
    print(f"  Y_22 = {Y_22}")
    
    # Expected form: sqrt(15/(16*pi)) * sin^2(theta) * cos(2*phi)
    expected_Y22_coeff = sqrt(15 / (16*pi))
    expected_Y22 = expected_Y22_coeff * sin(theta)**2 * cos(2*phi)
    print(f"  Expected: sqrt(15/(16*pi)) * sin^2(theta) * cos(2*phi) = {expected_Y22}")
    print(f"  Match: {simplify(Y_22 - expected_Y22) == 0}")
    
    # Y_30 verification
    print("\nY_30 verification:")
    Y_30 = harmonics[(3, 0)]
    print(f"  Y_30 = {Y_30}")
    
    # Expected: sqrt(7/(16*pi)) * (5*cos^3(theta) - 3*cos(theta))
    expected_Y30_coeff = sqrt(7 / (16*pi))
    expected_Y30 = expected_Y30_coeff * (5*cos(theta)**3 - 3*cos(theta))
    print(f"  Expected: sqrt(7/(16*pi)) * (5*cos^3(theta) - 3*cos(theta)) = {expected_Y30}")
    print(f"  Match: {simplify(Y_30 - expected_Y30) == 0}")
    
    # ============================================================
    # Part 3: Normalization Verification
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 3: Normalization Verification")
    print("=" * 70)
    
    print("\nVerifying: integral of Y_lm^2 over sphere = 1")
    print("Integral over sphere: int_0^2pi int_0^pi Y_lm^2 * sin(theta) dtheta dphi")
    
    # Test normalization for a few harmonics
    test_lm = [(0, 0), (1, 0), (1, 1), (2, 0), (2, 2)]
    
    print("\n" + "-" * 70)
    print(f"{'(l,m)':<10} {'Integral':<30} {'Expected':<15} {'Match?'}")
    print("-" * 70)
    
    for l, m in test_lm:
        Y_lm = harmonics[(l, m)]
        
        # Compute integral of Y_lm^2 over sphere
        # int_0^{2*pi} int_0^{pi} Y_lm^2 * sin(theta) dtheta dphi
        integrand = Y_lm**2 * sin(theta)
        
        integral_theta = integrate(integrand, (theta, 0, pi))
        integral_full = integrate(integral_theta, (phi, 0, 2*pi))
        
        result = simplify(integral_full)
        expected = 1
        match = (result == expected)
        
        print(f"({l},{m}){''<6} {str(result):<30} {expected:<15} {match}")
    
    # ============================================================
    # Part 4: Orthogonality Verification
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 4: Orthogonality Verification")
    print("=" * 70)
    
    print("\nVerifying: integral of Y_lm * Y_l'm' over sphere = delta_ll' * delta_mm'")
    
    # Test orthogonality for a few pairs
    test_pairs = [
        ((0, 0), (1, 0)),
        ((1, 0), (1, 1)),
        ((2, 0), (2, 2)),
        ((2, 0), (0, 0)),
    ]
    
    print("\n" + "-" * 70)
    print(f"{'(l,m)':<10} {'(l\',m\')':<10} {'Integral':<25} {'Expected':<15} {'Match?'}")
    print("-" * 70)
    
    for (l1, m1), (l2, m2) in test_pairs:
        Y1 = harmonics[(l1, m1)]
        Y2 = harmonics[(l2, m2)]

        integrand = Y1 * Y2 * sin(theta)
        integral_theta = integrate(integrand, (theta, 0, pi))
        integral_full = integrate(integral_theta, (phi, 0, 2*pi))
        result = simplify(integral_full)

        expected = 1 if (l1 == l2 and m1 == m2) else 0
        match = (result == expected)

        print(f"({l1},{m1}){'':<5} ({l2},{m2}){'':<5} {str(result):<25} {expected:<15} {match}")

    # ============================================================
    # Part 5: Relation to Geopotential (J2 connection)
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 5: Connection to Geopotential J2 Term")
    print("=" * 70)

    Y_20 = harmonics[(2, 0)]
    print(f"\nY_20 = {Y_20}")
    print(f"\nP_2(cos(theta)) = (3*cos^2(theta) - 1)/2")
    print(f"Y_20 = sqrt(5/(4*pi)) * (1/2) * (3*cos^2(theta) - 1)")
    print(f"     = sqrt(5/(4*pi)) * P_2(cos(theta))")
    print(f"\nThe J2 term in the geopotential uses P_2 (unnormalized),")
    print(f"which relates to Y_20 by: P_2 = sqrt(4*pi/5) * Y_20")

    print("\n" + "=" * 70)
    print("Script completed successfully!")
    print("=" * 70)

if __name__ == "__main__":
    main()