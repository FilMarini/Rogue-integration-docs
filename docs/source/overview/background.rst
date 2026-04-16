Background
==========

Rogue and the UDP Data Path
----------------------------

`Rogue <https://github.com/slaclab/rogue>`_ is SLAC's software framework for
interfacing with FPGA-based hardware. A typical rogue deployment connects to
an FPGA over a network using:

* **SRP (SLAC Register Protocol)** over UDP for AXI-lite register access (slow
  path — configuration, status)
* **RSSI + Packetizer** over UDP for streaming data (fast path — event data)

The fast path topology looks like::

    FPGA  ──UDP──►  rogue.protocols.udp
                        │
                    rogue.protocols.rssi
                        │
                    rogue.protocols.packetizer
                        │
                    pyrogue.Device (application)

This works well at gigabit speeds over a LAN, but has practical limits:

* UDP requires kernel involvement on every packet.
* RSSI adds per-packet sequence numbers and retransmission overhead.
* At 100 GbE line rates, software UDP receive becomes the bottleneck.

Why RoCEv2 / RDMA?
-------------------

**RDMA (Remote Direct Memory Access)** allows a remote device (here: the FPGA)
to write directly into host memory **without involving the host CPU** on the
data path. The host CPU is involved only when the transfer is complete — it
receives a *completion queue entry* (CQE) from the RDMA NIC.

**RoCEv2 (RDMA over Converged Ethernet v2)** is RDMA transported over standard
Ethernet/IP/UDP, making it deployable without InfiniBand hardware. It is the
dominant high-speed interconnect in modern data centers and is supported by
most 25 GbE and above NICs.

Key benefits over pure UDP in the rogue context:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Property
     - UDP (baseline)
     - RoCEv2 / RDMA
   * - CPU involvement per packet
     - Every packet
     - Zero (DMA direct to memory)
   * - Flow control
     - None (application layer)
     - Hardware credit-based (RC QP)
   * - Congestion control
     - None
     - DCQCN (hardware)
   * - Latency
     - ~µs (kernel overhead)
     - Sub-µs (bypass kernel)
   * - Bandwidth ceiling
     - ~10–40 Gbps practical
     - Line rate (100+ Gbps)

SLAC BSV RoCEv2 Engine
-----------------------

The FPGA firmware uses a custom RoCEv2 engine written in
`Bluespec SystemVerilog (BSV) <https://github.com/B-Lang-org/bsc>`_.  The
engine is a full hardware RDMA stack that:

* Manages its own **Protection Domain (PD)**, **Memory Region (MR)**, and
  **Queue Pair (QP)** resources internally.
* Is configured via an **AXI-lite register interface** using a structured
  metadata bus protocol (see :doc:`../metadata/overview`).
* Performs **RDMA WRITE-with-Immediate** operations — it actively pushes data
  frames into a memory region that the host has registered and advertised.
* Implements **DCQCN** (Data Center Quantized Congestion Notification) for
  hardware-accelerated congestion control (see :doc:`../dcqcn/overview`).

The SRP/UDP AXI-lite register path that rogue already uses to configure other
FPGA peripherals is reused as the **connection side-channel** — no new protocol
or TCP port is needed.
