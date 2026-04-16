RoCEv2 Integration in Rogue
============================

This documentation describes the integration of **RoCEv2 / RDMA** receive
capability into the `rogue` software framework developed at SLAC National
Accelerator Laboratory.

The integration allows rogue to receive high-speed data frames from an FPGA
equipped with a SLAC RoCEv2 engine performing **RDMA WRITE-with-Immediate**
operations, while preserving the same :mod:`pyrogue` usage patterns as the
existing UDP/RSSI-based workflow.

.. toctree::
   :maxdepth: 2
   :caption: Overview

   overview/background
   overview/architecture

.. toctree::
   :maxdepth: 2
   :caption: Integration Guide

   integration/quickstart
   integration/host_side
   integration/fpga_side
   integration/connection_flow
   integration/connection_lifecycle
   integration/dma_interface
   integration/test_firmware

.. toctree::
   :maxdepth: 2
   :caption: Metadata Channel

   metadata/overview
   metadata/bus_layout
   metadata/pd_messages
   metadata/mr_messages
   metadata/qp_messages
   metadata/response_decoding

.. toctree::
   :maxdepth: 2
   :caption: DCQCN Congestion Control

   dcqcn/overview
   dcqcn/registers

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/rocev2_server
   api/roce_engine
   api/cpp_server

.. toctree::
   :maxdepth: 1
   :caption: Appendices

   appendix/build
   appendix/troubleshooting
   appendix/glossary
