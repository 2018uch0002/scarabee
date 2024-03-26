#ifndef MOC_DRIVER_H
#define MOC_DRIVER_H

#include <moc/cartesian_2d.hpp>
#include <moc/boundary_condition.hpp>
#include <moc/flat_source_region.hpp>
#include <moc/track.hpp>
#include <moc/quadrature/polar_quadrature.hpp>

#include <memory>
#include <vector>

class MOCDriver {
 public:
  MOCDriver(std::shared_ptr<Cartesian2D> geometry, PolarQuadrature polar_quad,
            BoundaryCondition xmin = BoundaryCondition::Reflective,
            BoundaryCondition xmax = BoundaryCondition::Reflective,
            BoundaryCondition ymin = BoundaryCondition::Reflective,
            BoundaryCondition ymax = BoundaryCondition::Reflective);

  bool drawn() const { return !angle_info_.empty(); }

  void draw_tracks(std::uint32_t n_angles, double d);

  FlatSourceRegion& get_fsr(const Vector& r, const Direction& u);
  const FlatSourceRegion& get_fsr(const Vector& r, const Direction& u) const;

  PolarQuadrature& polar_quadrature() { return polar_quad_; }
  const PolarQuadrature& polar_quadrature() const { return polar_quad_; }

  std::size_t ngroups() { return ngroups_; }

  BoundaryCondition& x_min_bc() { return x_min_bc_; }
  const BoundaryCondition& x_min_bc() const { return x_min_bc_; }

  BoundaryCondition& x_max_bc() { return x_max_bc_; }
  const BoundaryCondition& x_max_bc() const { return x_max_bc_; }

  BoundaryCondition& y_min_bc() { return y_min_bc_; }
  const BoundaryCondition& y_min_bc() const { return y_min_bc_; }

  BoundaryCondition& y_max_bc() { return y_max_bc_; }
  const BoundaryCondition& y_max_bc() const { return y_max_bc_; }

 private:
  struct AngleInfo {
    double phi;        // Azimuthal angle for track
    double d;          // Spacing for trackings of this angle
    double wgt;        // Weight for tracks with this angle
    std::uint32_t nx;  // Number of tracks starting on the -y boundary
    std::uint32_t ny;  // Number of tracks starting on the -x boundary
  };

  std::vector<AngleInfo> angle_info_;       // Information for all angles
  std::vector<std::vector<Track>> tracks_;  // All tracks, indexed by angle
  std::vector<FlatSourceRegion*> fsrs_;     // All FSRs in the geometry
  std::shared_ptr<Cartesian2D> geometry_;   // Geometry for the problem
  PolarQuadrature polar_quad_;
  std::size_t ngroups_;
  BoundaryCondition x_min_bc_, x_max_bc_, y_min_bc_, y_max_bc_;

  void generate_azimuthal_quadrature(std::uint32_t n_angles, double d);
  void generate_tracks();
  void set_track_ends_bcs();
  void allocate_track_fluxes();
  void allocate_fsr_flux_source();
  void calculate_segment_exps();
};

#endif