#!/usr/bin/env sage -python
"""
04_j2_numerical.py

Numerical evaluation of J2 gravitational perturbation.

This script computes:
- Gravitational potential with J2 perturbation at specific points
- J2 acceleration vector in Cartesian coordinates
- Ratio of J2 perturbation to monopole term
- Grid analysis of J2 potential over sphere surface

Usage:
    sage -python 04_j2_numerical.py
"""

from sage.all import *

def main():
    print("=" * 70)
    print("J2 GRAVITATIONAL PERTURBATION - NUMERICAL EVALUATION")
    print("=" * 70)
    
    # ============================================================
    # Part 1: Define Constants
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 1: Physical Constants")
    print("=" * 70)
    
    # Earth gravitational parameters (SI units)
    mu = 3.986004418e14       # m^3/s^2 (GM)
    Re = 6378137.0            # m (equatorial radius)
    J2 = 1.08263e-3           # dimensionless
    
    print(f"\nmu (GM) = {mu:.6e} m^3/s^2")
    print(f"Re (equatorial radius) = {Re:.3f} m = {Re/1000:.3f} km")
    print(f"J2 = {J2:.6e}")
    
    # ============================================================
    # Part 2: Sample Point Calculation (ISS-like orbit)
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 2: Sample Point - ISS-like LEO Orbit")
    print("=" * 70)
    
    # ISS-like orbit: altitude ~400 km
    h = 400e3  # meters
    r = Re + h
    theta = pi/2  # equatorial
    phi = 0       # arbitrary
    
    print(f"\nOrbit parameters:")
    print(f"Altitude h = {h/1000:.1f} km")
    print(f"Radius r = Re + h = {r/1000:.3f} km = {r:.3f} m")
    print(f"theta = {float(theta):.6f} rad ({float(theta * 180/pi):.1f} deg)")
    print(f"phi = {float(phi):.6f} rad")
    
    # Position in Cartesian
    x = r * sin(theta) * cos(phi)
    y = r * sin(theta) * sin(phi)
    z = r * cos(theta)
    
    print(f"\nCartesian position:")
    print(f"x = {float(x):.3f} m")
    print(f"y = {float(y):.3f} m")
    print(f"z = {float(z):.3f} m")
    
    # ============================================================
    # Part 3: Gravitational Potential
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 3: Gravitational Potential")
    print("=" * 70)
    
    # Monopole potential
    V_mono = -mu / r
    print(f"\nMonopole potential:")
    print(f"V_monopole = -mu/r = {float(V_mono):.6e} J/kg (m^2/s^2)")
    
    # J2 perturbation potential
    P2 = (3*cos(theta)**2 - 1) / 2
    V_j2 = - (mu / r) * J2 * (Re/r)**2 * P2
    
    print(f"\nJ2 perturbation potential:")
    print(f"P_2(cos(theta)) = {float(P2):.6f}")
    print(f"V_J2 = {float(V_j2):.6e} J/kg")
    
    # Total potential
    V_total = V_mono + V_j2
    print(f"\nTotal potential:")
    print(f"V_total = V_monopole + V_J2 = {float(V_total):.6e} J/kg")
    
    # Ratio
    ratio_V = abs(V_j2 / V_mono)
    print(f"\n|V_J2 / V_monopole| = {float(ratio_V):.6e}")
    print(f"J2 perturbation is {float(ratio_V)*100:.4f}% of monopole")
    
    # ============================================================
    # Part 4: J2 Acceleration in Cartesian
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 4: J2 Acceleration Vector")
    print("=" * 70)
    
    # Monopole acceleration (pointing toward origin)
    r_vec = vector([x, y, z])
    r_mag = sqrt(x**2 + y**2 + z**2)
    
    a_mono = -mu / r_mag**3 * r_vec
    
    print(f"\nMonopole acceleration:")
    print(f"a_monopole = -mu/r^3 * r_vec")
    a_mono_numeric = [float(a_mono[i]) for i in range(3)]
    print(f"a_monopole = ({a_mono_numeric[0]:.6e}, {a_mono_numeric[1]:.6e}, {a_mono_numeric[2]:.6e}) m/s^2")
    
    # Magnitude
    a_mono_mag = sqrt(sum([a_mono[i]**2 for i in range(3)]))
    print(f"|a_monopole| = {float(a_mono_mag):.6e} m/s^2")
    
    # J2 acceleration using standard formula
    # a_J2_x = -3*mu*J2*Re^2*x*(1 - 5*z^2/r^2) / (2*r^5)
    r2 = r_mag**2
    r5 = r_mag**5
    
    factor = -3 * mu * J2 * Re**2 / (2 * r5)
    
    a_j2_x = factor * x * (1 - 5*z**2/r2)
    a_j2_y = factor * y * (1 - 5*z**2/r2)
    a_j2_z = factor * z * (3 - 5*z**2/r2)
    
    a_j2 = vector([a_j2_x, a_j2_y, a_j2_z])
    
    print(f"\nJ2 perturbation acceleration:")
    print(f"a_J2_x = {float(a_j2_x):.6e} m/s^2")
    print(f"a_J2_y = {float(a_j2_y):.6e} m/s^2")
    print(f"a_J2_z = {float(a_j2_z):.6e} m/s^2")
    
    a_j2_mag = sqrt(sum([a_j2[i]**2 for i in range(3)]))
    print(f"|a_J2| = {float(a_j2_mag):.6e} m/s^2")
    
    # Ratio
    ratio_a = float(a_j2_mag / a_mono_mag)
    print(f"\n|a_J2| / |a_monopole| = {ratio_a:.6e}")
    print(f"J2 acceleration is {ratio_a*100:.4f}% of monopole acceleration")
    
    # Total acceleration
    a_total = a_mono + a_j2
    print(f"\nTotal acceleration:")
    a_total_numeric = [float(a_total[i]) for i in range(3)]
    print(f"a_total = ({a_total_numeric[0]:.6e}, {a_total_numeric[1]:.6e}, {a_total_numeric[2]:.6e}) m/s^2")
    
    # ============================================================
    # Part 5: Grid Analysis - J2 Potential Over Sphere
    # ============================================================
    print("\n" + "=" * 70)
    print("PART 5: Grid Analysis - J2 Potential Variation")
    print("=" * 70)
    
    # At fixed radius, compute J2 potential for grid of (theta, phi)
    r_fixed = Re + 400e3  # Same altitude
    
    print(f"\nAnalyzing at fixed radius r = {float(r_fixed)/1000:.1f} km")
    print("\nJ2 potential depends only on theta (colatitude), not phi")
    print("(for zonal harmonics J2, J3, etc.)")
    
    # Sample at different theta values
    theta_samples = [0, pi/6, pi/4, pi/3, pi/2, 2*pi/3, 3*pi/4, 5*pi/6, pi]
    
    print(f"\n{'theta (deg)':<12} {'cos(theta)':<12} {'P_2(cos)':<12} {'V_J2 (m^2/s^2)':<20}")
    print("-" * 60)
    
    v_j2_values = []
    for th in theta_samples:
        cth = cos(th)
        p2 = (3*cth**2 - 1) / 2
        v_j2 = float(- (mu / r_fixed) * J2 * (Re/r_fixed)**2 * p2)
        v_j2_values.append((th, p2, v_j2))
        print(f"{float(th*180/pi):<12.1f} {float(cth):<12.4f} {float(p2):<12.4f} {v_j2:<20