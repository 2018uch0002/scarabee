from scarabee import *

name = "F31_0"

set_output_file(name+"_reflector_out.txt")

ndl = NDLibrary()

# Define all Materials
Fuel31Comp = MaterialComposition()
Fuel31Comp.fractions = Fraction.Atoms
Fuel31Comp.add_nuclide("O16",  4.5853e-02)
Fuel31Comp.add_nuclide("O17",  1.7420e-05)
Fuel31Comp.add_nuclide("O18",  9.1942e-05)
Fuel31Comp.add_nuclide("U234", 5.7987e-06)
Fuel31Comp.add_nuclide("U235", 7.2175e-04)
Fuel31Comp.add_nuclide("U238", 2.2253e-02)
Fuel31 = Material(Fuel31Comp, 575., ndl)

CladComp = MaterialComposition()
CladComp.fractions = Fraction.Atoms
CladComp.add_nuclide("Cr50",  3.2962e-06)
CladComp.add_nuclide("Cr52",  6.3564e-05)
CladComp.add_nuclide("Cr53",  7.2076e-06)
CladComp.add_nuclide("Cr54",  1.7941e-06)
CladComp.add_nuclide("Fe54",  8.6698e-06)
CladComp.add_nuclide("Fe56",  1.3610e-04)
CladComp.add_nuclide("Fe57",  3.1431e-06)
CladComp.add_nuclide("Fe58",  4.1829e-07)
CladComp.add_nuclide("O16",   3.0744e-04)
CladComp.add_nuclide("O17",   1.1680e-07)
CladComp.add_nuclide("O18",   6.1648e-07)
CladComp.add_nuclide("Sn112", 4.6735e-06)
CladComp.add_nuclide("Sn114", 3.1799e-06)
CladComp.add_nuclide("Sn115", 1.6381e-06)
CladComp.add_nuclide("Sn116", 7.0055e-05)
CladComp.add_nuclide("Sn117", 3.7003e-05)
CladComp.add_nuclide("Sn118", 1.1669e-04)
CladComp.add_nuclide("Sn119", 4.1387e-05)
CladComp.add_nuclide("Sn120", 1.5697e-04)
CladComp.add_nuclide("Sn122", 2.2308e-05)
CladComp.add_nuclide("Sn124", 2.7897e-05)
CladComp.add_nuclide("Zr90",  2.1828e-02)
CladComp.add_nuclide("Zr91",  4.7601e-03)
CladComp.add_nuclide("Zr92",  7.2759e-03)
CladComp.add_nuclide("Zr94",  7.3734e-03)
CladComp.add_nuclide("Zr96",  1.1879e-03)
Clad = Material(CladComp, 575., ndl)

HeComp = MaterialComposition()
HeComp.add_nuclide("He3", 4.8089e-10)
HeComp.add_nuclide("He4", 2.4044e-04)
He = Material(HeComp, 575., ndl) 

WaterComp = MaterialComposition()
WaterComp.add_nuclide("B10",     7.9714e-06)
WaterComp.add_nuclide("B11",     3.2247e-05)
WaterComp.add_nuclide("H1_H2O_TC",  4.9456e-02 + 7.7035e-06)
WaterComp.add_nuclide("O16",     2.4673e-02)
WaterComp.add_nuclide("O17",     9.3734e-06)
WaterComp.add_nuclide("O18",     4.9474e-05)
Water = Material(WaterComp, 575., ndl)

Bafflecomp = MaterialComposition()
Bafflecomp.fractions = Fraction.Atoms
Bafflecomp.add_nuclide("Cr50", 7.6778E-4)
Bafflecomp.add_nuclide("Cr52", 1.4806E-2)
Bafflecomp.add_nuclide("Cr53", 1.6789E-3)
Bafflecomp.add_nuclide("Cr54", 4.1791E-4)
Bafflecomp.add_nuclide("Fe54", 3.4620E-3)
Bafflecomp.add_nuclide("Fe56", 5.4345E-2)
Bafflecomp.add_nuclide("Fe57", 1.2551E-3)
Bafflecomp.add_nuclide("Fe58", 1.6703E-4)
Bafflecomp.add_nuclide("Mn55", 1.7604E-3)
Bafflecomp.add_nuclide("Ni58", 5.6089E-3)
Bafflecomp.add_nuclide("Ni60", 2.1605E-3)
Bafflecomp.add_nuclide("Ni61", 9.3917E-5)
Bafflecomp.add_nuclide("Ni62", 2.9945E-4)
Bafflecomp.add_nuclide("Ni64", 7.6261E-5)
Bafflecomp.add_nuclide("Si28", 9.5281E-4)
Bafflecomp.add_nuclide("Si29", 4.8381E-5)
Bafflecomp.add_nuclide("Si30", 3.1893E-5)
Baffle = Material(Bafflecomp, 575., ndl)

# Define a guide tube
gt = GuideTube(inner_radius=0.56134, outer_radius=0.60198, clad=Clad)

# Define fuel pin
fp = FuelPin(fuel=Fuel31, fuel_radius=0.39218, gap=He, gap_radius=0.40005, clad=Clad, clad_radius=0.45720)

# Define assembly
asmbly = PWRAssembly(pitch=1.25984, moderator=Water, shape=(17, 17), ndl=ndl)
asmbly.pins = [fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp,
               fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp,
               fp, fp, fp, fp, fp, gt, fp, fp, gt, fp, fp, gt, fp, fp, fp, fp, fp,
               fp, fp, fp, gt, fp, fp, fp, fp, fp, fp, fp, fp, fp, gt, fp, fp, fp,
               fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp,
               fp, fp, gt, fp, fp, gt, fp, fp, gt, fp, fp, gt, fp, fp, gt, fp, fp,
               fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp,
               fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp,
               fp, fp, gt, fp, fp, gt, fp, fp, gt, fp, fp, gt, fp, fp, gt, fp, fp,
               fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp,
               fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp,
               fp, fp, gt, fp, fp, gt, fp, fp, gt, fp, fp, gt, fp, fp, gt, fp, fp,
               fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp,
               fp, fp, fp, gt, fp, fp, fp, fp, fp, fp, fp, fp, fp, gt, fp, fp, fp,
               fp, fp, fp, fp, fp, gt, fp, fp, gt, fp, fp, gt, fp, fp, fp, fp, fp,
               fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp,
               fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp, fp]
asmbly.solve()
asmbly.save_diffusion_data(name+".npz")

# Solve reflector
print()
refl = Reflector(asmbly.average_fuel_pin, moderator=asmbly.moderator_xs,
                 assembly_width=21.50364, gap_width=0.1627,
                 baffle_width=2.2225, baffle=Baffle, ndl=ndl)
refl.solve()
refl.save_diffusion_data("reflector.npz")
