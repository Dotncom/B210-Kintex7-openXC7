# Licensing and provenance

- The FPGA patches target the OpenSourceSDRLab B210 Kintex-7 project and the
  Ettus Research HDL it incorporates. Keep the original notices and licenses
  of the files to which they apply. The Ettus HDL touched here carries
  `LGPL-3.0-or-later` notices. OpenSourceSDRLab lists its repository as GPL-3.0.
- The UHD GNSS and GSV patches target Ettus Research UHD v4.3.0.0. The modified
  host files carry `GPL-3.0-or-later` notices.
- The separately authored RTL and simulation fixtures in this repository
  use LGPL-3.0-or-later. The Python and shell build scripts and documentation
  use GPL-3.0-or-later.

The GPL and LGPL texts are in [`licenses/`](licenses/). The build reads an
independently supplied vendor project and stock image locally. The repository
contains changes and build code. FPGA images, vendor archives and generated
toolchain databases are separate inputs or outputs.
