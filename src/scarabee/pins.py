from _scarabee import *
import numpy as np
from scipy.optimize import curve_fit, dual_annealing
from lmfit import Minimizer, create_params
from typing import Optional

import matplotlib.pyplot as plt

_fit_bounds = (-1000., 1000.)

class FuelPin:
    """
    Represents a fuel pin, contianing its geometric and material properties.

    Parameters
    ----------
    fuel : Material
        Material representing the fuel composition, temperature, and density.
    fuel_radius : float
        Radius of the fuel pellet.
    clad: Material
        Material representing the cladding composition, temperature, and
        density.
    clad_width : float
        Thickness of the cladding.
    gap : Material, optional
        Material representing the gap composition, temperature, and density.
    gap_width: float, optional
        Thickness of the gap between the fuel pellet and the cladding
        (if modeled).
    fuel_rings: int
        The number of rings into which the fuel pellet will be divided.
        Default value is 1.
    """

    def __init__(
        self,
        fuel: Material,
        fuel_radius: float,
        clad: Material,
        clad_width: float,
        gap: Optional[Material] = None,
        gap_width: Optional[float] = None,
        fuel_rings: int = 1
    ):
        self.fuel = fuel
        self.fuel_radius = fuel_radius
        self.clad = clad
        self.clad_width = clad_width
        self.gap = gap
        self.gap_width = gap_width
        self.fuel_rings = fuel_rings
        self.condensed_xs = []
        
        # Arrays which will hold the values used in the least square fitting
        # for determining self shielding terms
        self.fuel_xs_vals = []
        self.fuel_flux_vals = []
        self.clad_xs_vals = []
        self.clad_flux_vals = []
        
        self.fuel_a = []
        self.fuel_b = []
        self.clad_a = []
        self.clad_b = []

        if self.gap is not None and self.gap_width is None:
            raise RuntimeError("Fuel gap material is provided, but no gap width.")
        elif self.gap_width is not None and self.gap is None:
            raise RuntimeError("Fuel gap width provided, but no gap material.")

        if fuel_rings <= 0:
            raise RuntimeError("The number of fuel rings must be >= 1.")

    def determine_fuel_self_shielding_params(self):
        l = 2.*self.fuel_radius
        Ep = self.fuel.potential_xs

        params = create_params(l=dict(value=l,    vary=False),
                               Ep=dict(value=Ep,  vary=False),
                               a1=dict(value=0.1, vary=True, min=0., max=2.),
                               a2=dict(value=-0.2, vary=True, min=-2., max=0.),
                               b1=dict(value=2.,  vary=True, min=-20., max=20.)
                              )
        def P(params, Et, flux):
            l = params['l']
            Ep = params['Ep']
            a1 = params['a1']
            a2 = params['a2']
            b1 = params['b1']
            b2 = 1. - b1
            model = b1*((Ep*l + a1)/(Et*l + a1)) + b2*((Ep*l + a2)/(Et*l + a2))
            return model - flux

        def J(params, Et, flux):
            l = params['l']
            Ep = params['Ep']
            a1 = params['a1']
            a2 = params['a2']
            b1 = params['b1']
            b2 = 1. - b1
            return np.array([b1*l*(Et - Ep)/((l*Et + a1)*(l*Et + a1)), b2*l*(Et - Ep)/((l*Et + a2)*(l*Et + a2)), ((Ep*l + a1)/(Et*l + a1)) - ((Ep*l + a2)/(Et*l + a2))]).transpose()

        fitter = Minimizer(P, params, fcn_args=(np.array(self.fuel_xs_vals), np.array(self.fuel_flux_vals)), Dfun=J)
        result = fitter.minimize(method='differential_evolution')
        self.fuel_a = [result.params['a1'].value, result.params['a2'].value]
        self.fuel_b = [result.params['b1'].value, 1. - result.params['b1'].value]

    def plot_fuel_ss(self):
        l = 2.*self.fuel_radius
        Ep = self.fuel.potential_xs

        def P(Et):
            val = 0.
            for i in range(len(self.fuel_a)):
                a = self.fuel_a[i]
                b = self.fuel_b[i]
                val += b*((Ep*l + a)/(Et*l + a))
            return val

        plt.plot(np.logspace(-5., 5., 500), P(np.logspace(-5., 5., 500)), c='red')
        plt.scatter(self.fuel_xs_vals, self.fuel_flux_vals)
        plt.xscale('log')
        plt.show()

    def determine_clad_self_shielding_params(self):
        Rin = self.fuel_radius
        if self.gap_width is not None:
            Rin += self.gap_width
        Rout = Rin + self.clad_width
        l = 2.*(Rout - Rin)
        Ep = self.clad.potential_xs
        
        params = create_params(l=dict(value=l,    vary=False),
                               Ep=dict(value=Ep,  vary=False),
                               a1=dict(value=0.1, vary=True, min=0., max=2.),
                               a2=dict(value=-0.2, vary=True, min=-2., max=0.),
                               b1=dict(value=2.,  vary=True, min=-20., max=20.)
                              )
        def P(params, Et, flux):
            l = params['l']
            Ep = params['Ep']
            a1 = params['a1']
            a2 = params['a2']
            b1 = params['b1']
            b2 = 1. - b1
            model = b1*((Ep*l + a1)/(Et*l + a1)) + b2*((Ep*l + a2)/(Et*l + a2))
            return model - flux

        def J(params, Et, flux):
            l = params['l']
            Ep = params['Ep']
            a1 = params['a1']
            a2 = params['a2']
            b1 = params['b1']
            b2 = 1. - b1
            return np.array([b1*l*(Et - Ep)/((l*Et + a1)*(l*Et + a1)), b2*l*(Et - Ep)/((l*Et + a2)*(l*Et + a2)), ((Ep*l + a1)/(Et*l + a1)) - ((Ep*l + a2)/(Et*l + a2))]).transpose()

        fitter = Minimizer(P, params, fcn_args=(np.array(self.clad_xs_vals), np.array(self.clad_flux_vals)), Dfun=J)
        result = fitter.minimize(method='differential_evolution')
        self.clad_a = [result.params['a1'].value, result.params['a2'].value]
        self.clad_b = [result.params['b1'].value, 1. - result.params['b1'].value]

    def plot_clad_ss(self):
        Rin = self.fuel_radius
        if self.gap_width is not None:
            Rin += self.gap_width
        Rout = Rin + self.clad_width
        l = 2.*(Rout - Rin)
        Ep = self.clad.potential_xs
        def P(Et):
            val = 0.
            for i in range(len(self.clad_a)):
                a = self.clad_a[i]
                b = self.clad_b[i]
                val += b*((Ep*l + a)/(Et*l + a))
            return val

        plt.plot(np.logspace(-5., 5., 500), P(np.logspace(-5., 5., 500)), c='red')
        plt.scatter(self.clad_xs_vals, self.clad_flux_vals)
        plt.xscale('log')
        plt.show()

    def clad_offset(self):
        if self.gap_width is not None:
            return Vector(
                self.fuel_radius + self.gap_width + 0.5 * self.clad_width, 0.0
            )
        else:
            return Vector(self.fuel_radius + 0.5 * self.clad_width, 0.0)

    def make_fuel_dancoff_cell(self, pitch: float, xs: float, moderator: Material):
        # We first determine all the radii
        radii = []
        radii.append(self.fuel_radius)
        if self.gap is not None:
            radii.append(radii[-1] + self.gap_width)
        radii.append(radii[-1] + self.clad_width)

        mats = []

        # This returns a cell for calculating the fuel pin Dancoff factor.
        # As such, the fuel XS has infinite values.
        Et = np.array([xs])
        Ea = np.array([xs])
        Es = np.array([[0.0]])
        Fuel = CrossSection(Et, Ea, Es, "Fuel")
        mats.append(Fuel)

        if self.gap is not None:
            Et[0] = self.gap.potential_xs
            Ea[0] = self.gap.potential_xs
            gap = CrossSection(Et, Ea, Es, "Gap")
            mats.append(gap)

        Et[0] = self.clad.potential_xs
        Ea[0] = self.clad.potential_xs
        Clad = CrossSection(Et, Ea, Es, "Clad")
        mats.append(Clad)

        Et[0] = moderator.potential_xs
        Ea[0] = moderator.potential_xs
        Mod = CrossSection(Et, Ea, Es, "Moderator")
        mats.append(Mod)

        return SimplePinCell(radii, mats, pitch, pitch)

    def make_clad_dancoff_cell(self, pitch: float, xs: float, moderator: Material):
        # We first determine all the radii
        radii = []
        radii.append(self.fuel_radius)
        if self.gap is not None:
            radii.append(radii[-1] + self.gap_width)
        radii.append(radii[-1] + self.clad_width)

        mats = []

        Et = np.array([self.fuel.potential_xs])
        Ea = np.array([self.fuel.potential_xs])
        Es = np.array([[0.0]])
        Fuel = CrossSection(Et, Ea, Es, "Fuel")
        mats.append(Fuel)

        if self.gap is not None:
            Et[0] = self.gap.potential_xs
            Ea[0] = self.gap.potential_xs
            gap = CrossSection(Et, Ea, Es, "Gap")
            mats.append(gap)

        # This returns a cell for calculating the fuel pin Dancoff factor.
        # As such, the clad XS has infinite values.
        Et[0] = xs 
        Ea[0] = xs 
        Clad = CrossSection(Et, Ea, Es, "Clad")
        mats.append(Clad)

        Et[0] = moderator.potential_xs
        Ea[0] = moderator.potential_xs
        Mod = CrossSection(Et, Ea, Es, "Moderator")
        mats.append(Mod)

        return SimplePinCell(radii, mats, pitch, pitch)

    def make_cylindrical_cell(
        self,
        pitch: float,
        dancoff_fuel: float,
        moderator: CrossSection,
        ndl: NDLibrary,
        dancoff_clad: Optional[float] = None,
        clad_dilution=1.0e10,
    ):
        # We first determine all the radii
        radii = []

        # Add the fuel radius
        if self.fuel_rings == 1:
            radii.append(self.fuel_radius)
        else:
            # We need to subdivide the pellet into rings. We start be getting
            # the fuel pellet volume
            V = np.pi * self.fuel_radius * self.fuel_radius
            Vring = V / float(self.fuel_rings)
            for r in range(self.fuel_rings):
                Rin = 0.
                if r > 0:
                    Rin = radii[-1]
                Rout = np.sqrt((Vring + np.pi*Rin*Rin)/np.pi)
                if Rout > self.fuel_radius:
                  Rout = self.fuel_radius
                radii.append(Rout)

        # Add gap radius
        if self.gap is not None:
            radii.append(radii[-1] + self.gap_width)

        # Add clad radius
        radii.append(radii[-1] + self.clad_width)

        # Add water radius
        radii.append(np.sqrt(pitch * pitch / np.pi))

        # Next, we determine all the materials.
        # This requires applying self shielding to the fuel and cladding
        mats = []

        # First, treat the fuel
        if self.fuel_rings == 1:
            # For a single pellet, use the standard Carlvik two-term
            Ee = 1.0 / (2.0 * self.fuel_radius)  # Fuel escape xs
            mats.append(self.fuel.carlvik_xs(dancoff_fuel, Ee, ndl))
            mats[-1].name = "Fuel"
        else:
            # We need to apply spatial self shielding.
            for r in range(self.fuel_rings):
                Rin = 0.
                if r > 0:
                    Rin = radii[r-1]
                Rout = radii[r]
                mats.append(self.fuel.ring_carlvik_xs(dancoff_fuel, self.fuel_radius, Rin, Rout, ndl))
                mats[-1].name = "Fuel"

        # Next, add the gap (if present)
        if self.gap is not None:
            mats.append(self.gap.dilution_xs(self.gap.size * [1.0e10], ndl))
            mats[-1].name = "Gap"

        # Add the cladding
        if dancoff_clad is not None:
            Ee = 1.0 / (2.0 * self.clad_width)
            mats.append(self.clad.roman_xs(dancoff_clad, Ee, ndl))
        else:
            mats.append(self.clad.dilution_xs(self.clad.size * [clad_dilution], ndl))
        mats[-1].name = "Clad"

        # Finally, add moderator
        mats.append(moderator)

        return CylindricalCell(radii, mats)

    def make_moc_cell(self, pitch: float):
        radii = []

        if self.fuel_rings == 1:
            radii.append(self.fuel_radius)
        else:
            # We need to subdivide the pellet into rings. We start be getting
            # the fuel pellet volume
            V = np.pi * self.fuel_radius * self.fuel_radius
            Vring = V / float(self.fuel_rings)
            for r in range(self.fuel_rings):
                Rin = 0.
                if r > 0:
                    Rin = radii[-1]
                Rout = np.sqrt((Vring + np.pi*Rin*Rin)/np.pi)
                radii.append(Rout)

        if self.gap is not None:
            radii.append(radii[-1] + self.gap_width)

        radii.append(radii[-1] + self.clad_width)

        mod_width = 0.5 * pitch - radii[-1]
        radii.append(radii[-1] + 0.8 * mod_width)

        mats = self.condensed_xs.copy()
        mats.append(self.condensed_xs[-1])

        return PinCell(radii, mats, pitch, pitch)


class GuideTube:
    """
    Represents an empty guide tube, contianing its geometric and material
    properties.

    Parameters
    ----------
    inner_radius : float
        Inside radius of the guide tube.
    outer_radius : float
        Outside radius of the guide tube.
    clad : Material
        Material representing the guide tube composition, temperature, and
        density (assumed to be the same material as the fuel pin cladding).
    """

    def __init__(self, inner_radius: float, outer_radius: float, clad: Material):
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
        self.clad = clad
        self.condensed_xs = []
        
        # Arrays which will hold the values used in the least square fitting
        # for determining self shielding terms
        self.clad_xs_vals = []
        self.clad_flux_vals = []

        self.clad_a = []
        self.clad_b = []

        if self.outer_radius <= self.inner_radius:
            raise RuntimeError("Outer radius must be > inner radius.")
    
    def determine_clad_self_shielding_params(self):
        l = 2.*(self.outer_radius - self.inner_radius)
        Ep = self.clad.potential_xs
        
        params = create_params(l=dict(value=l,    vary=False),
                               Ep=dict(value=Ep,  vary=False),
                               a1=dict(value=0.1, vary=True, min=0., max=2.),
                               a2=dict(value=-0.2, vary=True, min=-2., max=0.),
                               b1=dict(value=2.,  vary=True, min=-20., max=20.)
                              )
        def P(params, Et, flux):
            l = params['l']
            Ep = params['Ep']
            a1 = params['a1']
            a2 = params['a2']
            b1 = params['b1']
            b2 = 1. - b1
            model = b1*((Ep*l + a1)/(Et*l + a1)) + b2*((Ep*l + a2)/(Et*l + a2))
            return model - flux

        def J(params, Et, flux):
            l = params['l']
            Ep = params['Ep']
            a1 = params['a1']
            a2 = params['a2']
            b1 = params['b1']
            b2 = 1. - b1
            return np.array([b1*l*(Et - Ep)/((l*Et + a1)*(l*Et + a1)), b2*l*(Et - Ep)/((l*Et + a2)*(l*Et + a2)), ((Ep*l + a1)/(Et*l + a1)) - ((Ep*l + a2)/(Et*l + a2))]).transpose()

        fitter = Minimizer(P, params, fcn_args=(np.array(self.clad_xs_vals), np.array(self.clad_flux_vals)), Dfun=J)
        result = fitter.minimize(method='differential_evolution')
        self.clad_a = [result.params['a1'].value, result.params['a2'].value]
        self.clad_b = [result.params['b1'].value, 1. - result.params['b1'].value]

    def plot_clad_ss(self):
        l = 2.*(self.outer_radius - self.inner_radius)
        Ep = self.clad.potential_xs
        def P(Et):
            val = 0.
            for i in range(len(self.clad_a)):
                a = self.clad_a[i]
                b = self.clad_b[i]
                val += b*((Ep*l + a)/(Et*l + a))
            return val

        plt.plot(np.logspace(-5., 5., 500), P(np.logspace(-5., 5., 500)), c='red')
        plt.scatter(self.clad_xs_vals, self.clad_flux_vals)
        plt.xscale('log')
        plt.show()

    def clad_offset(self):
        return Vector(0.5 * (self.inner_radius + self.outer_radius), 0.0)

    def make_clad_dancoff_cell(self, pitch: float, xs: float, moderator: Material):
        # We first determine all the radii
        radii = []
        radii.append(self.inner_radius)
        radii.append(self.outer_radius)

        mats = []

        Et = np.array([moderator.potential_xs])
        Ea = np.array([moderator.potential_xs])
        Es = np.array([[0.0]])
        Mod = CrossSection(Et, Ea, Es, "Moderator")
        mats.append(Mod)

        # This returns a cell for calculating the fuel pin Dancoff factor.
        # As such, the clad XS has infinite values.
        Et[0] = xs 
        Ea[0] = xs 
        Clad = CrossSection(Et, Ea, Es, "Clad")
        mats.append(Clad)

        mats.append(Mod)

        return SimplePinCell(radii, mats, pitch, pitch)

    def make_fuel_dancoff_cell(self, pitch: float, xs: float, moderator: Material):
        # We first determine all the radii
        radii = []
        radii.append(self.inner_radius)
        radii.append(self.outer_radius)

        mats = []

        Et = np.array([moderator.potential_xs])
        Ea = np.array([moderator.potential_xs])
        Es = np.array([[0.0]])
        Mod = CrossSection(Et, Ea, Es, "Moderator")
        mats.append(Mod)

        Et[0] = self.clad.potential_xs
        Ea[0] = self.clad.potential_xs
        Clad = CrossSection(Et, Ea, Es, "Clad")
        mats.append(Clad)

        mats.append(Mod)

        return SimplePinCell(radii, mats, pitch, pitch)

    def make_cylindrical_cell(
        self,
        pitch: float,
        moderator: CrossSection,
        buffer_radius: float,
        buffer: CrossSection,
        ndl: NDLibrary,
        dancoff_clad: Optional[float] = None,
        clad_dilution: float = 1.0e10,
    ):
        # We first determine all the radii
        radii = []
        radii.append(self.inner_radius)
        radii.append(self.outer_radius)
        radii.append(np.sqrt(pitch * pitch / np.pi))
        if radii[-1] >= buffer_radius:
            raise RuntimeError("Buffer radius is smaller than the radius of the cell.")
        radii.append(buffer_radius)

        # Next, we determine all the materials.
        # This requires applying self shielding to the fuel and cladding
        mats = []

        mats.append(moderator)

        # Add the cladding
        if dancoff_clad is not None:
            Ee = 1.0 / (2.0 * (self.outer_radius - self.inner_radius))
            mats.append(self.clad.roman_xs(dancoff_clad, Ee, ndl))
        else:
            mats.append(self.clad.dilution_xs(self.clad.size * [clad_dilution], ndl))
        mats[-1].name = "Clad"

        # Add outer moderator
        mats.append(moderator)

        # Add the buffer
        mats.append(buffer)

        return CylindricalCell(radii, mats)

    def make_moc_cell(self, pitch: float):
        r_inner_inner_mod = np.sqrt(0.5 * self.inner_radius * self.inner_radius)
        radii = [r_inner_inner_mod, self.inner_radius, self.outer_radius]
        mats = [self.condensed_xs[0]] + self.condensed_xs.copy()
        return PinCell(radii, mats, pitch, pitch)

