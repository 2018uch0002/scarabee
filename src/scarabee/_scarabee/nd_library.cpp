#include <data/nd_library.hpp>
#include <utils/constants.hpp>
#include <utils/logging.hpp>
#include <utils/scarabee_exception.hpp>

#include <xtensor/xtensor.hpp>

#include <cmath>
#include <sstream>

namespace scarabee {

void NuclideHandle::load_xs_from_hdf5(const NDLibrary& ndl) {
  if (this->loaded()) return;

  auto grp = ndl.h5()->getGroup(this->name);

  // Create and allocate arrays
  absorption = std::make_shared<xt::xtensor<double, 3>>();
  absorption->resize({temperatures.size(), dilutions.size(), ndl.ngroups()});
  scatter = std::make_shared<xt::xtensor<double, 4>>();
  scatter->resize(
      {temperatures.size(), dilutions.size(), ndl.ngroups(), ndl.ngroups()});
  p1_scatter = std::make_shared<xt::xtensor<double, 4>>();
  p1_scatter->resize(
      {temperatures.size(), dilutions.size(), ndl.ngroups(), ndl.ngroups()});
  if (this->fissile) {
    fission = std::make_shared<xt::xtensor<double, 3>>();
    fission->resize({temperatures.size(), dilutions.size(), ndl.ngroups()});
    nu = std::make_shared<xt::xtensor<double, 2>>();
    nu->resize({temperatures.size(), ndl.ngroups()});
    chi = std::make_shared<xt::xtensor<double, 2>>();
    chi->resize({temperatures.size(), ndl.ngroups()});
  }

  // Read in data
  grp.getDataSet("absorption").read_raw<double>(absorption->data());
  grp.getDataSet("scatter").read_raw<double>(scatter->data());
  grp.getDataSet("p1-scatter").read_raw<double>(p1_scatter->data());
  if (this->fissile) {
    grp.getDataSet("fission").read_raw<double>(fission->data());
    grp.getDataSet("nu").read_raw<double>(nu->data());
    grp.getDataSet("chi").read_raw<double>(chi->data());
  }
}

void NuclideHandle::unload() {
  absorption = nullptr;
  scatter = nullptr;
  p1_scatter = nullptr;
  fission = nullptr;
  chi = nullptr;
  nu = nullptr;
}

NDLibrary::NDLibrary(const std::string& fname)
    : nuclide_handles_(),
      group_bounds_(),
      library_(),
      group_structure_(),
      ngroups_(0),
      h5_(nullptr) {
  // Make sure HDF5 file exists
  if (std::filesystem::exists(fname) == false) {
    std::stringstream mssg;
    mssg << "The file \"" << fname << "\" does not exist.";
    spdlog::error(mssg.str());
    throw ScarabeeException(mssg.str());
  }

  // Open the HDF5 file
  h5_ = std::make_shared<H5::File>(fname, H5::File::ReadOnly);

  // Get info on library
  if (h5_->hasAttribute("library"))
    library_ = h5_->getAttribute("library").read<std::string>();
  if (h5_->hasAttribute("group-structure"))
    group_structure_ = h5_->getAttribute("group-structure").read<std::string>();
  if (h5_->hasAttribute("group-bounds"))
    group_bounds_ =
        h5_->getAttribute("group-bounds").read<std::vector<double>>();
  if (h5_->hasAttribute("ngroups"))
    ngroups_ = h5_->getAttribute("ngroups").read<std::size_t>();

  // Read all nuclide handles
  auto nuc_names = h5_->listObjectNames();
  for (const auto& nuc : nuc_names) {
    auto grp = h5_->getGroup(nuc);

    nuclide_handles_.emplace(std::make_pair(nuc, NuclideHandle()));
    auto& handle = nuclide_handles_.at(nuc);
    handle.name = nuc;

    // Read nuclide info
    handle.label = grp.getAttribute("label").read<std::string>();
    handle.temperatures =
        grp.getAttribute("temperatures").read<std::vector<double>>();
    handle.awr = grp.getAttribute("awr").read<double>();
    handle.potential_xs = grp.getAttribute("potential-xs").read<double>();
    handle.ZA = grp.getAttribute("ZA").read<std::uint32_t>();
    handle.fissile = grp.getAttribute("fissile").read<bool>();
    handle.resonant = grp.getAttribute("resonant").read<bool>();
    handle.dilutions =
        grp.getAttribute("dilutions").read<std::vector<double>>();
  }
}

const NuclideHandle& NDLibrary::get_nuclide(const std::string& name) const {
  if (nuclide_handles_.find(name) == nuclide_handles_.end()) {
    std::stringstream mssg;
    mssg << "Could not find nuclde by name of \"" << name << "\".";
    spdlog::error(mssg.str());
    throw ScarabeeException(mssg.str());
  }

  return nuclide_handles_.at(name);
}

void NDLibrary::unload() {
  for (auto& nuc_handle : nuclide_handles_) {
    nuc_handle.second.unload();
  }
}

NuclideHandle& NDLibrary::get_nuclide(const std::string& name) {
  if (nuclide_handles_.find(name) == nuclide_handles_.end()) {
    std::stringstream mssg;
    mssg << "Could not find nuclde by name of \"" << name << "\".";
    spdlog::error(mssg.str());
    throw ScarabeeException(mssg.str());
  }

  return nuclide_handles_.at(name);
}

std::shared_ptr<CrossSection> NDLibrary::interp_xs(const std::string& name,
                                                   const double temp,
                                                   const double dil) {
  auto& nuc = this->get_nuclide(name);

  // Get temperature interpolation factors
  std::size_t it = 0;  // temperature index
  double f_temp = 0.;  // temperature interpolation factor
  get_temp_interp_params(temp, nuc, it, f_temp);

  // Get dilution interpolation factors
  std::size_t id = 0;  // dilution index
  double f_dil = 0.;   // dilution interpolation factor
  get_dil_interp_params(dil, nuc, id, f_dil);

  if (nuc.loaded() == false) {
    nuc.load_xs_from_hdf5(*this);
  }

  //--------------------------------------------------------
  // Do absorption interpolation
  xt::xtensor<double, 1> Ea;
  this->interp_1d(Ea, *nuc.absorption, it, f_temp, id, f_dil);

  //--------------------------------------------------------
  // Do scattering interpolation
  xt::xtensor<double, 2> Es;
  this->interp_2d(Es, *nuc.scatter, it, f_temp, id, f_dil);

  //--------------------------------------------------------
  // Do p1 scattering interpolation
  xt::xtensor<double, 2> Es1;
  this->interp_2d(Es1, *nuc.p1_scatter, it, f_temp, id, f_dil);

  //--------------------------------------------------------
  // Do fission interpolation
  xt::xtensor<double, 1> Ef = xt::zeros<double>({ngroups_});
  xt::xtensor<double, 1> nu = xt::zeros<double>({ngroups_});
  xt::xtensor<double, 1> chi = xt::zeros<double>({ngroups_});
  if (nuc.fissile) {
    this->interp_1d(Ef, *nuc.fission, it, f_temp, id, f_dil);
    this->interp_1d(nu, *nuc.nu, it, f_temp);
    this->interp_1d(chi, *nuc.chi, it, f_temp);
  }

  // Reconstruct total, removing p1
  xt::xtensor<double, 1> Et = xt::zeros<double>({ngroups_});
  for (std::size_t g = 0; g < ngroups_; g++) {
    Et(g) = Ea(g) + xt::sum(xt::view(Es, g, xt::all()))();
    Et(g) -= Es1(g, g);
    Es(g, g) -= Es1(g, g);
  }

  // Make temp CrossSection
  return std::make_shared<CrossSection>(Et, Ea, Es, Ef, nu * Ef, chi);
}

std::shared_ptr<CrossSection> NDLibrary::two_term_xs(
    const std::string& name, const double temp, const double b1,
    const double b2, const double bg_xs_1, const double bg_xs_2) {
  // See reference [1] to understand this interpolation scheme, in addition to
  // the calculation of the flux based on the pot_xs and sig_a.

  // Get the two cross section sets
  auto xs_1 = interp_xs(name, temp, bg_xs_1);
  auto xs_2 = interp_xs(name, temp, bg_xs_2);

  const double pot_xs = get_nuclide(name).potential_xs;

  xt::xtensor<double, 1> Et = xt::zeros<double>({ngroups_});
  xt::xtensor<double, 1> Ea = xt::zeros<double>({ngroups_});
  xt::xtensor<double, 2> Es = xt::zeros<double>({ngroups_, ngroups_});
  xt::xtensor<double, 1> Ef = xt::zeros<double>({ngroups_});
  xt::xtensor<double, 1> vEf = xt::zeros<double>({ngroups_});
  xt::xtensor<double, 1> chi = xt::zeros<double>({ngroups_});
  xt::xtensor<double, 2> Es1 = xt::zeros<double>({ngroups_, ngroups_});

  double vEf_sum_1 = 0.;
  double vEf_sum_2 = 0.;
  for (std::size_t g = 0; g < ngroups_; g++) {
    // Calculate the two flux values
    const double flux_1_g =
        (pot_xs + bg_xs_1) / (xs_1->Ea(g) + pot_xs + bg_xs_1);
    const double flux_2_g =
        (pot_xs + bg_xs_2) / (xs_2->Ea(g) + pot_xs + bg_xs_2);

    // Calcualte the two weighting factors
    const double f1_g = b1 * flux_1_g / (b1 * flux_1_g + b2 * flux_2_g);
    const double f2_g = b2 * flux_2_g / (b1 * flux_1_g + b2 * flux_2_g);

    // Compute the xs values
    Ea(g) = f1_g * xs_1->Ea(g) + f2_g * xs_2->Ea(g);
    Ef(g) = f1_g * xs_1->Ef(g) + f2_g * xs_2->Ef(g);
    for (std::size_t g_out = 0; g_out < ngroups_; g_out++) {
      Es(g, g_out) = f1_g * xs_1->Es(g, g_out) + f2_g * xs_2->Es(g, g_out);
      Es1(g, g_out) = f1_g * xs_1->Es1(g, g_out) + f2_g * xs_2->Es1(g, g_out);
    }
    Et(g) = Ea(g) + xt::sum(xt::view(Es, g, xt::all()))();

    const double vEf1 = f1_g * xs_1->vEf(g);
    const double vEf2 = f2_g * xs_2->vEf(g);
    vEf(g) = vEf1 + vEf2;
    vEf_sum_1 += vEf1;
    vEf_sum_2 += vEf2;
  }

  if (vEf_sum_1 + vEf_sum_2 > 0.) {
    double chi_sum = 0;
    for (std::size_t g = 0; g < ngroups_; g++) {
      chi(g) = (vEf_sum_1 * xs_1->chi(g) + vEf_sum_2 * xs_2->chi(g)) /
               (vEf_sum_1 + vEf_sum_2);
      chi_sum += chi(g);
    }
    if (chi_sum > 0.) chi /= chi_sum;
  }

  return std::make_shared<CrossSection>(Et, Ea, Es, Es1, Ef, vEf, chi);
}

std::shared_ptr<CrossSection> NDLibrary::ring_two_term_xs(
    const std::string& name, const double temp, const double a1,
    const double a2, const double b1, const double b2, const double mat_pot_xs,
    const double N, const double Rfuel, const double Rin, const double Rout) {
  if (Rin >= Rout) {
    auto mssg = "Rin must be < Rout.";
    spdlog::error(mssg);
    throw ScarabeeException(mssg);
  }

  if (Rout > Rfuel) {
    auto mssg = "Rout must be < Rfuel.";
    spdlog::error(mssg);
    throw ScarabeeException(mssg);
  }

  const auto& nuclide = get_nuclide(name);
  const double pot_xs = nuclide.potential_xs;
  const double macro_pot_xs = N * pot_xs;

  xt::xtensor<double, 1> Et = xt::zeros<double>({ngroups_});
  xt::xtensor<double, 1> Ea = xt::zeros<double>({ngroups_});
  xt::xtensor<double, 2> Es = xt::zeros<double>({ngroups_, ngroups_});
  xt::xtensor<double, 1> Ef = xt::zeros<double>({ngroups_});
  xt::xtensor<double, 1> vEf = xt::zeros<double>({ngroups_});
  xt::xtensor<double, 1> chi = xt::zeros<double>({ngroups_});
  xt::xtensor<double, 2> Es1 = xt::zeros<double>({ngroups_, ngroups_});

  // Denominators of the weighting factor for each energy group.
  xt::xtensor<double, 1> denoms = xt::zeros<double>({ngroups_});

  for (std::size_t m = 1; m <= 4; m++) {
    const std::pair<double, double> eta_lm = this->eta_lm(m, Rfuel, Rin, Rout);
    const double eta_m = eta_lm.first;
    const double l_m = eta_lm.second;

    // Calculate the background xs
    const double bg_xs_1 =
        l_m > 0. ? (mat_pot_xs - macro_pot_xs + a1 / l_m) / N : 1.E10;
    const double bg_xs_2 =
        l_m > 0. ? (mat_pot_xs - macro_pot_xs + a2 / l_m) / N : 1.E10;

    // Get the two cross section sets
    auto xs_1 = interp_xs(name, temp, bg_xs_1);
    auto xs_2 = interp_xs(name, temp, bg_xs_2);

    for (std::size_t g = 0; g < ngroups_; g++) {
      // Calculate the two flux values
      const double flux_1_g =
          (pot_xs + bg_xs_1) / (xs_1->Ea(g) + pot_xs + bg_xs_1);
      const double flux_2_g =
          (pot_xs + bg_xs_2) / (xs_2->Ea(g) + pot_xs + bg_xs_2);

      // Add contributions to the denominator
      denoms(g) += eta_m * (b1 * flux_1_g + b2 * flux_2_g);

      // Add contributions to the xs
      // Compute the xs values
      Ea(g) += eta_m * (b1 * xs_1->Ea(g) + b2 * xs_2->Ea(g));
      Ef(g) += eta_m * (b1 * xs_1->Ef(g) + b2 * xs_2->Ef(g));
      vEf(g) += eta_m * (b1 * xs_1->vEf(g) + b2 * xs_2->vEf(g));
      for (std::size_t g_out = 0; g_out < ngroups_; g_out++) {
        Es(g, g_out) +=
            eta_m * (b1 * xs_1->Es(g, g_out) + b2 * xs_2->Es(g, g_out));

        Es1(g, g_out) +=
            eta_m * (b1 * xs_1->Es1(g, g_out) + b2 * xs_2->Es1(g, g_out));
      }  // For all outgoing groups

      // Save the fission spectrum if we are in the first lump.
      // This assumes that the fission spectrum is dilution independent,
      // which is an okay approximation. I am not sure how to completely
      // handle the fission spectrum otherwise for this self shielding.
      if (m == 1) {
        chi(g) = xs_1->chi(g);
      }
    }  // For all groups
  }  // For 4 lumps

  // Now we go through and normalize each group by the denom, and calculate Et
  for (std::size_t g = 0; g < ngroups_; g++) {
    const double invs_denom = 1. / denoms(g);
    Ea(g) *= invs_denom;
    Ef(g) *= invs_denom;
    vEf(g) *= invs_denom;
    Et(g) = Ea(g);
    for (std::size_t g_out = 0; g_out < ngroups_; g_out++) {
      Es(g, g_out) *= invs_denom;
      Et(g) += Es(g, g_out);

      Es1(g, g_out) *= invs_denom;
    }
  }

  return std::make_shared<CrossSection>(Et, Ea, Es, Es1, Ef, vEf, chi);
}

void NDLibrary::get_temp_interp_params(double temp, const NuclideHandle& nuc,
                                       std::size_t& i, double& f) const {
  if (temp <= nuc.temperatures.front()) {
    i = 0;
    f = 0.;
    return;
  } else if (temp >= nuc.temperatures.back()) {
    i = nuc.temperatures.size() - 2;
    f = 1.;
    return;
  }

  for (i = 0; i < nuc.temperatures.size() - 1; i++) {
    double T_i = nuc.temperatures[i];
    double T_i1 = nuc.temperatures[i + 1];

    if (temp >= T_i && temp <= T_i1) {
      f = (std::sqrt(temp) - std::sqrt(T_i)) /
          (std::sqrt(T_i1) - std::sqrt(T_i));
      break;
    }
  }
  if (f < 0.)
    f = 0.;
  else if (f > 1.)
    f = 1.;
}

void NDLibrary::get_dil_interp_params(double dil, const NuclideHandle& nuc,
                                      std::size_t& i, double& f) const {
  if (dil <= nuc.dilutions.front()) {
    i = 0;
    f = 0.;
    return;
  } else if (dil >= nuc.dilutions.back()) {
    i = nuc.dilutions.size() - 2;
    f = 1.;
    return;
  }

  for (i = 0; i < nuc.dilutions.size() - 1; i++) {
    double d_i = nuc.dilutions[i];
    double d_i1 = nuc.dilutions[i + 1];

    if (dil >= d_i && dil <= d_i1) {
      f = (dil - d_i) / (d_i1 - d_i);
      break;
    }
  }
  if (f < 0.)
    f = 0.;
  else if (f > 1.)
    f = 1.;
}

void NDLibrary::interp_1d(xt::xtensor<double, 1>& E,
                          const xt::xtensor<double, 2> nE, std::size_t it,
                          double f_temp) const {
  if (f_temp > 0.) {
    E = (1. - f_temp) * xt::view(nE, it, xt::all()) +
        f_temp * xt::view(nE, it + 1, xt::all());
  } else {
    E = xt::view(nE, it, xt::all());
  }
}

void NDLibrary::interp_1d(xt::xtensor<double, 1>& E,
                          const xt::xtensor<double, 3> nE, std::size_t it,
                          double f_temp, std::size_t id, double f_dil) const {
  if (f_temp > 0.) {
    if (f_dil > 0.) {
      E = (1. - f_temp) * ((1. - f_dil) * xt::view(nE, it, id, xt::all()) +
                           f_dil * xt::view(nE, it, id + 1, xt::all())) +
          f_temp * ((1. - f_dil) * xt::view(nE, it + 1, id, xt::all()) +
                    f_dil * xt::view(nE, it + 1, id + 1, xt::all()));
    } else {
      E = (1. - f_temp) * xt::view(nE, it, id, xt::all()) +
          f_temp * xt::view(nE, it + 1, id, xt::all());
    }
  } else {
    if (f_dil > 0.) {
      E = (1. - f_dil) * xt::view(nE, it, id, xt::all()) +
          f_dil * xt::view(nE, it, id + 1, xt::all());
    } else {
      E = xt::view(nE, it, id, xt::all());
    }
  }
}

void NDLibrary::interp_2d(xt::xtensor<double, 2>& E,
                          const xt::xtensor<double, 4> nE, std::size_t it,
                          double f_temp, std::size_t id, double f_dil) const {
  if (f_temp > 0.) {
    if (f_dil > 0.) {
      E = (1. - f_temp) *
              ((1. - f_dil) * xt::view(nE, it, id, xt::all(), xt::all()) +
               f_dil * xt::view(nE, it, id + 1, xt::all(), xt::all())) +
          f_temp *
              ((1. - f_dil) * xt::view(nE, it + 1, id, xt::all(), xt::all()) +
               f_dil * xt::view(nE, it + 1, id + 1, xt::all(), xt::all()));
    } else {
      E = (1. - f_temp) * xt::view(nE, it, id, xt::all(), xt::all()) +
          f_temp * xt::view(nE, it + 1, id, xt::all(), xt::all());
    }
  } else {
    if (f_dil > 0.) {
      E = (1. - f_dil) * xt::view(nE, it, id, xt::all(), xt::all()) +
          f_dil * xt::view(nE, it, id + 1, xt::all(), xt::all());
    } else {
      E = xt::view(nE, it, id, xt::all(), xt::all());
    }
  }
}

std::pair<double, double> NDLibrary::eta_lm(std::size_t m, double Rfuel,
                                            double Rin, double Rout) const {
  if (m == 0 || m > 4) {
    auto mssg = "Invalid m.";
    spdlog::error(mssg);
    throw ScarabeeException(mssg);
  }

  // Shouldn't need to check m, as this is a private method
  const double p_i = std::min(Rout / Rfuel, 1.);
  const double p_im = Rin / Rfuel;

  double p = p_i;
  if (m == 3 || m == 4) p = p_im;

  double theta = 0.5 * PI * p;
  if (m == 2 || m == 4) theta = -theta;

  // l = 4V_ring / S_pin = 4 pi (Rout^2 - Rin^2) / (2 pi Rfuel)
  const double l = 2. * (Rout * Rout - Rin * Rin) / Rfuel;

  const double T1 = std::sqrt(1. - p * p);
  const double T2 = Rin > 0. ? std::asin(p) / p : 1.;

  const double lm = (2. * Rfuel / PI) * (T1 + T2 + theta);

  double eta = p * lm / l;
  if (m == 2 || m == 3) eta = -eta;

  return {eta, lm};
}

}  // namespace scarabee

// References
// [1] H. Koike, K. Yamaji, K. Kirimura, D. Sato, H. Matsumoto, and A. Yamamoto,
//     “Advanced resonance self-shielding method for gray resonance treatment in
//     lattice physics code GALAXY,” J. Nucl. Sci. Technol., vol. 49, no. 7,
//     pp. 725–747, 2012, doi: 10.1080/00223131.2012.693885.
