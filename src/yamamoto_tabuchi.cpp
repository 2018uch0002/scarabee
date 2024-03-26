#include <moc/quadrature/yamamoto_tabuchi.hpp>

// A. YAMAMOTO, M. TABUCHI, N. SUGIMURA, T. USHIO, and M. MORI, “Derivation of
// Optimum Polar Angle Quadrature Set for the Method of Characteristics Based on
// Approximation Error for the Bickley Function,” J. Nucl. Sci. Technol., vol.
// 44, no. 2, pp. 129–136, 2007, doi: 10.1080/18811248.2007.9711266.

// N = 2
template <>
const std::array<double, 1> YamamotoTabuchi<2>::abscissae_ = {0.798184};
template <>
const std::array<double, 1> YamamotoTabuchi<2>::weights_ = {1.000000};

// N = 4
template <>
const std::array<double, 2> YamamotoTabuchi<4>::abscissae_ = {0.363900,
                                                              0.899900};
template <>
const std::array<double, 2> YamamotoTabuchi<4>::weights_ = {0.212854, 0.787146};

// N = 6
template <>
const std::array<double, 3> YamamotoTabuchi<6>::abscissae_ = {
    0.166648, 0.537707, 0.932954};
template <>
const std::array<double, 3> YamamotoTabuchi<6>::weights_ = {0.046233, 0.283619,
                                                            0.670148};