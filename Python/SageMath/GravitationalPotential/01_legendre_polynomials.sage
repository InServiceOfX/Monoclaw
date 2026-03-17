#!/usr/bin/env sage -python
"""
01_legendre_polynomials.py

Symbolic computation of Legendre polynomials and associated Legendre functions.

This script computes:
- Legendre polynomials P_n(x) for n = 0 to 6
- Associated Legendre functions P_nm(cos(theta)) for relevant (n,m) pairs
- Verifies orthogonality: integral of P_n(x)*P_m(x) from -1 to 1
- Plots P_0 through P_5 over the interval [-1, 1]

Usage:
    sage -python 01_legendre_polynomials.py
"""

from sage.all import *

def main():
    print("=" * 70)
    print("LEGENDRE POLYNOMIALS - SYMBOLIC COMPUTATION")
    print("=" * 70)
    
    # Define symbolic variable
    x = var('x')
    theta = var('theta')
    
    # ============================================================
    # Part 1: Legendre Polynomials P_n(x) for n = 0 to 6
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 1: Legendre Polynomials P_n(x)")
    print("=" * 70)
    
    # Using Sage's built-in legendre_P function
    legendre_polys = {}
    
    for n in range(7):
        P_n = legendre_P(n, x)
        legendre_polys[n] = P_n
        
        print(f"\nP_{n}(x) = {P_n}")
        print(f"LaTeX: ${latex(P_n)}$")
        
        # Also show expanded form
        P_n_expanded = expand(P_n)
        if P_n_expanded != P_n:
            print(f"Expanded: {P_n_expanded}")
    
    # ============================================================
    # Part 2: Verify Rodrigues' Formula for P_n(x)
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 2: Verification of Rodrigues' Formula")
    print("=" * 70)
    
    print("\nRodrigues' formula: P_n(x) = (1/(2^n n!)) d^n/dx^n [(x^2 - 1)^n]")
    
    for n in range(4):
        # Rodrigues' formula
        rodrigues = (1 / (2**n * factorial(n))) * diff((x**2 - 1)**n, x, n)
        rodrigues_simplified = simplify(rodrigues)
        
        # Built-in Legendre
        builtin = legendre_P(n, x)
        
        # Check if they match
        match = simplify(rodrigues_simplified - builtin) == 0
        
        print(f"\nn = {n}:")
        print(f"  Rodrigues: {rodrigues_simplified}")
        print(f"  Built-in:  {builtin}")
        print(f"  Match: {match}")
    
    # ============================================================
    # Part 3: Associated Legendre Functions P_nm(cos(theta))
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 3: Associated Legendre Functions P_nm(cos(theta))")
    print("=" * 70)
    
    # Relevant (n,m) pairs for gravitational potential
    nm_pairs = [(1, 0), (1, 1), (2, 0), (2, 1), (2, 2), 
                (3, 0), (3, 1), (3, 2), (3, 3)]
    
    print("\nAssociated Legendre functions P_nm(cos(theta)):")
    
    for n, m in nm_pairs:
        P_nm = gen_legendre_P(n, m, cos(theta))
        P_nm_simplified = simplify(P_nm)
        
        print(f"\nP_{n},{m}(cos(theta)) = {P_nm_simplified}")
        print(f"LaTeX: ${latex(P_nm_simplified)}$")
    
    # ============================================================
    # Part 4: Orthogonality Verification
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 4: Orthogonality Verification")
    print("=" * 70)
    
    print("\nVerifying: integral of P_n(x) * P_m(x) from -1 to 1")
    print("Expected: 2/(2n+1) * delta_nm")
    
    print("\n" + "-" * 70)
    print(f"{'n':<5} {'m':<5} {'Integral':<30} {'Expected':<20} {'Match?'}")
    print("-" * 70)
    
    for n in range(5):
        for m in range(5):
            P_n = legendre_P(n, x)
            P_m = legendre_P(m, x)
            
            # Compute integral
            integral_result = integrate(P_n * P_m, (x, -1, 1))
            
            # Expected result
            if n == m:
                expected = 2 / (2*n + 1)
            else:
                expected = 0
            
            # Check match
            match = (integral_result == expected)
            
            print(f"{n:<5} {m:<5} {str(integral_result):<30} {str(expected):<20} {match}")
    
    # ============================================================
    # Part 5: Special Values
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 5: Special Values")
    print("=" * 70)
    
    print("\nP_n(1) = 1 for all n:")
    for n in range(6):
        val = legendre_P(n, 1)
        print(f"  P_{n}(1) = {val}")
    
    print("\nP_n(-1) = (-1)^n:")
    for n in range(6):
        val = legendre_P(n, -1)
        expected = (-1)**n
        print(f"  P_{n}(-1) = {val} (expected: {expected})")
    
    print("\nP_n(0) for odd/even n:")
    for n in range(6):
        val = legendre_P(n, 0)
        print(f"  P_{n}(0) = {val}")
    
    # ============================================================
    # Part 6: Plotting
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 6: Plotting Legendre Polynomials")
    print("=" * 70)
    
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        import numpy as np
        
        print("\nGenerating plot...")
        
        # Create plot
        fig, ax = plt.subplots(figsize=(10, 6))
        
        x_vals = np.linspace(-1, 1, 500)
        
        colors = ['black', 'red', 'blue', 'green', 'purple', 'orange']
        
        for n in range(6):
            # Evaluate polynomial
            P_n = legendre_P(n, x)
            y_vals = [float(P_n.subs(x=val)) for val in x_vals]
            
            ax.plot(x_vals, y_vals, label=f'P_{n}(x)', 
                   color=colors[n % len(colors)], linewidth=2)
        
        ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
        ax.axvline(x=0, color='k', linestyle='-', linewidth=0.5)
        ax.set_xlabel('x', fontsize=12)
        ax.set_ylabel('P_n(x)', fontsize=12)
        ax.set_title('Legendre Polynomials P_0 through P_5', fontsize=14)
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1.2, 1.2)
        
        plt.tight_layout()
        out_path = '/work/legendre_polynomials.png'
        plt.savefig(out_path, dpi=150)
        print(f"Plot saved to: {out_path}")
        print("On your host machine that is:")
        print("  ~/.openclaw/workspace/repos/Monoclaw/Python/SageMath/GravitationalPotential/legendre_polynomials.png")
        
    except ImportError as e:
        print(f"\nMatplotlib not available in Sage environment: {e}")
        print("Skipping plot generation.")
    except Exception as e:
        print(f"\nError generating plot: {e}")
        print("Skipping plot generation.")
    
    print("\n" + "=" * 70)
    print("Script completed successfully!")
    print("=" * 70)

if __name__ == "__main__":
    main()
