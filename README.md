# RoCEv2 Integration in Rogue — Documentation

This repository contains the ReadTheDocs / Sphinx documentation for the
RoCEv2/RDMA receive integration into the
[rogue](https://github.com/slaclab/rogue) software framework developed at
SLAC National Accelerator Laboratory.

## Contents

| Section | Description |
|---|---|
| **Overview** | Background on RDMA, RoCEv2, and the SLAC BSV engine |
| **Integration Guide** | Host setup, FPGA setup, and connection flow |
| **Metadata Channel** | Complete bit-level documentation of the PD/MR/QP metadata bus |
| **DCQCN** | Congestion control overview and register map |
| **API Reference** | Python (`RoCEv2Server`, `RoceEngine`) and C++ (`Server`) APIs |
| **Appendices** | Build instructions, troubleshooting, glossary |

## Building the Docs Locally

```bash
pip install -r docs/requirements.txt
cd docs
make html
open build/html/index.html
```

## ReadTheDocs

This repository is configured for automatic builds on
[ReadTheDocs](https://readthedocs.org) via `.readthedocs.yaml`.

## Licence

SLAC National Accelerator Laboratory —
see [LICENSE.txt](https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html).
