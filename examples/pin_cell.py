from scarabee import *
import numpy as np
import matplotlib.pyplot as plt

ndl = NDLibrary()

UO2comp = MaterialComposition()
UO2comp.add_nuclide("U235", 7.0803E-4)
UO2comp.add_nuclide("U238", 2.2604E-2)
UO2comp.add_nuclide("O16",  4.6624E-2)
UO2 = Material(UO2comp, 293.6, ndl)

Zirccomp = MaterialComposition()
Zirccomp.add_nuclide("Zr90", 2.2200E-2)
Zirccomp.add_nuclide("Zr91", 4.8280E-3)
Zirccomp.add_nuclide("Zr92", 7.3713E-3)
Zirccomp.add_nuclide("Zr94", 7.5006E-3)
Zirccomp.add_nuclide("Zr96", 1.2070E-3)
Zirc = Material(Zirccomp, 293.6, ndl)

Watercomp = MaterialComposition()
Watercomp.add_nuclide("H1_H2O", 6.6630E-2)
Watercomp.add_nuclide("O16",    3.3315E-2)
Water = Material(Watercomp, 293.6, ndl)

Et = np.array([1.E5])
Ea = np.array([1.E5])
Es = np.array([[0.]])
Fuel = CrossSection(Et, Ea, Es, "Fuel")

Et = np.array([Zirc.potential_xs])
Ea = np.array([Zirc.potential_xs])
Clad = CrossSection(Et, Ea, Es, "Clad")

Et = np.array([Water.potential_xs])
Ea = np.array([Water.potential_xs])
Mod = CrossSection(Et, Ea, Es, "Mod")

# Define Cells
pitch = 1.26
iso_pitch = 500.*pitch
fuel_rad = 0.4095
clad_rad = 0.475

# Simulate isolated geometry
radii = [fuel_rad, clad_rad]
mats =  [Fuel, Clad, Mod]
isolated_pin = SimplePinCell(radii, mats, iso_pitch, iso_pitch)
iso_c2d = Cartesian2D([iso_pitch], [iso_pitch])
iso_c2d.set_tiles([isolated_pin])
iso_moc = MOCDriver(iso_c2d)
for i in range(iso_moc.nfsr):
  i_xs = iso_moc.xs(i)
  if i_xs.name == "Fuel":
    iso_moc.set_extern_src(i, 0, 0.)
  elif i_xs.name == "Clad":
    iso_moc.set_extern_src(i, 0, Zirc.potential_xs)
  else:
    iso_moc.set_extern_src(i, 0, Water.potential_xs)
iso_moc.sim_mode = SimulationMode.FixedSource
iso_moc.generate_tracks(128, 0.02, YamamotoTabuchi6())
iso_moc.flux_tolerance = 1.E-6
iso_moc.solve()

# Simulate real geomemtry
radii = [fuel_rad, clad_rad]
mats =  [Fuel, Clad, Mod]
P = SimplePinCell(radii, mats, pitch, pitch)
c2d = Cartesian2D([pitch], [pitch])
c2d.set_tiles([P])
moc = MOCDriver(c2d)
# Set the source
for i in range(moc.nfsr):
  i_xs = moc.xs(i)
  if i_xs.name == "Fuel":
    moc.set_extern_src(i, 0, 0.)
  elif i_xs.name == "Clad":
    moc.set_extern_src(i, 0, Zirc.potential_xs)
  else:
    moc.set_extern_src(i, 0, Water.potential_xs)
moc.generate_tracks(128, 0.02, YamamotoTabuchi6())
moc.flux_tolerance = 1.E-6
moc.sim_mode = SimulationMode.FixedSource
moc.solve()

# Calculate Dancoff correction factor
iso_flux = iso_moc.flux(Vector(0.,0.), Direction(1.,0.), 0)
flux = moc.flux(Vector(0.,0.), Direction(1.,0.), 0)
RR = flux * 1.E5 # Reaction rate in fuel
C = (iso_flux - flux) / iso_flux
print("Dancoff Correction: {}".format(C))
print("Dancoff Factor    : {}".format(1.-C))

# Create fuel xs
Ee = 1. / (2. * fuel_rad)
Fuel = UO2.carlvik_xs(C, Ee, ndl)

# Create cladding xs using a reference dilution
Clad = Zirc.dilution_xs(Zirc.size*[300.], ndl)

# Create moderator xs using a somewhat random dilution (shouldn't matter except a little bit on O16)
Mod = Water.dilution_xs(Water.size*[10.], ndl)

# Create and run full real problem with MOC
radii = [0.5*fuel_rad, 0.8*fuel_rad, fuel_rad, clad_rad, 1.2*clad_rad]
mats  = [Fuel,         Fuel,         Fuel,     Clad,     Mod,         Mod]
P = PinCell(radii, mats, pitch, pitch)
c2d = Cartesian2D([pitch], [pitch])
c2d.set_tiles([P])
moc = MOCDriver(c2d)
moc.generate_tracks(128, 0.005, YamamotoTabuchi6())
moc.flux_tolerance = 1.E-6
moc.solve()

print()
print()

# Solve same problem with CP
radii = [0.5*fuel_rad, 0.8*fuel_rad, fuel_rad, clad_rad, 1.2*clad_rad, pitch/np.sqrt(np.pi)]
mats  = [Fuel,         Fuel,         Fuel,     Clad,     Mod,         Mod]
cell = CylindricalCell(radii, mats)
cell.solve()
cell_flux = CylindricalFluxSolver(cell)
cell_flux.flux_tolerance = 1.E-6
cell_flux.solve()