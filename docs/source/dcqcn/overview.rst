DCQCN Overview
==============

What is DCQCN?
--------------

**DCQCN (Data Center Quantized Congestion Notification)** is a hardware-based
congestion control algorithm designed for RDMA over Converged Ethernet (RoCE)
networks.  It was introduced in the paper:

    *Zhu et al., "Congestion Control for Large-Scale RDMA Deployments",
    SIGCOMM 2015.*

DCQCN operates entirely in hardware — the NIC (or in this case, the FPGA's
RoCEv2 engine) reacts to congestion signals without host CPU involvement,
making it compatible with the zero-copy, kernel-bypass goals of RDMA.

Why It Matters Here
-------------------

Without congestion control, a 10 GbE RDMA flow can overwhelm switch buffers
and cause packet drops, which degrade to retransmission storms that kill
throughput.  In detector readout at SLAC, data bursts can be large and
irregular, making DCQCN essential for stable operation.

The SLAC RoCEv2 engine implements DCQCN natively.  The host configures
its parameters via AXI-lite registers (see :doc:`registers`).

Algorithm Summary
-----------------

DCQCN uses three interacting components:

1. **ECN Marking at the Switch** — When a switch queue exceeds a threshold,
   it marks packets with the ECN CE (Congestion Experienced) bit in the IP
   header instead of dropping them.

2. **CNP Generation at the Receiver** — When the receiver (the host NIC in
   this integration) receives an ECN-marked packet, it sends a
   **Congestion Notification Packet (CNP)** back to the sender (the FPGA).
   The host NIC generates CNPs automatically — no software involvement.

3. **Rate Reduction at the Sender (FPGA)** — When the FPGA receives a CNP,
   it runs the DCQCN rate reduction algorithm:

   * Computes a new **alpha** (congestion estimate):
     ``α ← (1 − g) · α + g · 1``  on each CNP.
   * Reduces the **current rate**:
     ``Rc ← Rc · (1 − α/2)``
   * Clamps to a minimum rate.
   * Schedules **rate recovery** timers.

4. **Rate Recovery (no CNPs)** — When no CNPs arrive for ``RateIncInt``
   microseconds, the FPGA increases the rate:

   * **Additive Increase (AI)**: ``Rc ← Rc + Rai`` every ``RateIncInt``
   * **Hyper-Active Increase (HAI)**: after ``K`` consecutive AI steps
     without a CNP, switch to ``Rc ← Rc + Rhai``

State Machine
-------------

The DCQCN state machine in the FPGA has three states:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - State
     - Description
   * - **Fast Recovery**
     - Entered on CNP receipt.  Rate drops immediately.  Alpha timer runs.
   * - **Additive Increase**
     - No recent CNPs.  Rate increases by ``Rai`` every ``RateIncInt``.
   * - **Hyper-Active Increase**
     - Sustained AI steps without CNPs.  Rate increases faster by ``Rhai``.

The full state machine transitions and timing are described in the SIGCOMM
2015 paper; this documentation focuses on the register interface for
tuning.

ECN Configuration on the Switch
---------------------------------

For DCQCN to function, the network switch must be configured to mark ECN on
congested queues.  Typical settings:

* Enable ECN (rather than tail-drop) on the relevant switch port queues.
* Set ``K_min`` and ``K_max`` queue thresholds appropriate for the link speed
  and RTT (refer to your switch vendor documentation and the DCQCN paper for
  guidance).
* Configure DSCP-to-queue mapping if using QoS.

The host NIC must also have ECN enabled.  With MLNX_OFED or ``rdma-core``,
this is typically the default for RoCEv2 mode.

Default Parameter Values
-------------------------

The following defaults are used in ``RoCEv2Server._start()`` when writing
DCQCN registers.  They are suitable for a 10 GbE FPGA-to-host link and
can be tuned via pyrogue variables after startup:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Parameter
     - Default
     - Notes
   * - ``RateIncInt``
     - 5 µs
     - Rate increase interval
   * - ``RateDecInt``
     - 4 µs
     - Rate decrease interval (CNP reaction window)
   * - ``AlphaUpdateInt``
     - 55 µs
     - Interval for alpha decay without CNPs
   * - ``AlphaG``
     - 1/1024 (≈ 0.001)
     - EWMA weight for alpha update (stored as ``1 − g`` in 10-bit fixed
       point: ``ALPHA_G = round((1 − g) × 1024)``)
   * - ``ClampTgtRate``
     - 0 (off)
     - When 1, clamps target rate to current rate on CNP
   * - ``R_ai``
     - 50 Mbps
     - Additive increase step
   * - ``R_hai``
     - 500 Mbps
     - Hyper-active increase step

See :doc:`registers` for the AXI-lite register map.
