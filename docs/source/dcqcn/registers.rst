DCQCN Registers
================

The DCQCN parameters are exposed as AXI-lite registers in the RoCEv2 engine
register block.  They are configured by the host via SRP/UDP using pyrogue
``RemoteVariable`` entries in the ``RoceEngine`` device.

All timing registers store values in **clock cycles** (cc), not microseconds.
The conversion is::

    value_cc = round(value_us × clock_freq_MHz)

For a 250 MHz FPGA clock: ``1 µs = 250 cc``.

The helper used in ``_RoceEngine.py``::

    def us_to_cc(us: float, freq_mhz: float = 250.0) -> int:
        return round(us * freq_mhz)

    def mbps_to_byteps(mbps: float) -> int:
        return round(mbps * 1e6 / 8)

Register Map
------------

.. list-table::
   :header-rows: 1
   :widths: 12 12 12 12 52

   * - Offset
     - Bit range
     - Width
     - Name
     - Description
   * - ``0x000``
     - ``[31:0]``
     - 32
     - ``RateIncInt``
     - Rate increase interval in clock cycles.
       Additive increase step is applied every this many cc when no CNP
       is received.
       *Type*: UInt32 (cc).
       *Default*: ``us_to_cc(5)`` = 1250 cc @ 250 MHz.
   * - ``0x004``
     - ``[31:0]``
     - 32
     - ``RateDecInt``
     - Rate decrease / reaction interval in clock cycles.
       Controls how quickly the engine reacts to consecutive CNPs.
       *Type*: UInt32 (cc).
       *Default*: ``us_to_cc(4)`` = 1000 cc.
   * - ``0x008``
     - ``[31:0]``
     - 32
     - ``AlphaUpdateInt``
     - Alpha update (decay) interval in clock cycles.
       When no CNP is received for this interval, alpha decays toward 0.
       *Type*: UInt32 (cc).
       *Default*: ``us_to_cc(55)`` = 13750 cc.
   * - ``0x00C``
     - ``[9:0]``
     - 10
     - ``AlphaG``
     - Alpha EWMA weight in 10-bit fixed point.
       The firmware computes ``α ← (1 − g) · α + g · 1`` on each CNP,
       where the stored value is ``round((1 − g) × 1024)``.
       A value of 1023 means ``g ≈ 0.001`` (slow adaptation);
       a value of 512 means ``g = 0.5`` (fast adaptation).
       *Type*: UInt10 (fixed-point, dimensionless).
       *Default*: 1023 (``g ≈ 0.001``).
   * - ``0x010``
     - ``[0]``
     - 1
     - ``ClampTgtRate``
     - When ``1``, the target rate is clamped to the current rate upon
       receiving a CNP, preventing overshoot during recovery.
       When ``0`` (default), the target rate is not modified by CNPs.
       *Type*: Bool.
       *Default*: 0.
   * - ``0x014``
     - ``[31:0]``
     - 32
     - ``R_ai``
     - Additive increase (AI) step in bytes/second.
       Applied to the current rate every ``RateIncInt`` when no CNP.
       *Type*: UInt32 (bytes/sec).
       *Default*: ``mbps_to_byteps(50)`` = 6,250,000 B/s = 50 Mbps.
   * - ``0x018``
     - ``[31:0]``
     - 32
     - ``R_hai``
     - Hyper-active increase (HAI) step in bytes/second.
       Applied instead of ``R_ai`` when the engine has been in additive
       increase for ``K`` consecutive intervals without a CNP.
       *Type*: UInt32 (bytes/sec).
       *Default*: ``mbps_to_byteps(500)`` = 62,500,000 B/s = 500 Mbps.

.. note::
   The register addresses shown (``0x000``–``0x018``) are **relative to the
   DCQCN sub-block base address** within the RoCEv2 engine AXI-lite space.
   Add the engine's base offset when constructing ``RemoteVariable`` entries.

   Example: if the RoCEv2 engine is mapped at ``0x0000_A000`` in the FPGA
   address space, then ``R_ai`` is at absolute address ``0x0000_A014``.

PyRogue Variable Definitions
-----------------------------

These variables should be added to the ``RoceEngine`` pyrogue Device:

.. code-block:: python

    # DCQCN registers
    self.add(pr.RemoteVariable(
        name        = 'DcqcnRateIncInt',
        description = 'Rate increase interval (clock cycles). '
                      '1 us = 250 cc at 250 MHz.',
        offset      = 0x000,
        bitSize     = 32,
        mode        = 'RW',
        units       = 'cc',
    ))

    self.add(pr.RemoteVariable(
        name        = 'DcqcnRateDecInt',
        description = 'Rate decrease interval (clock cycles).',
        offset      = 0x004,
        bitSize     = 32,
        mode        = 'RW',
        units       = 'cc',
    ))

    self.add(pr.RemoteVariable(
        name        = 'DcqcnAlphaUpdateInt',
        description = 'Alpha decay interval (clock cycles).',
        offset      = 0x008,
        bitSize     = 32,
        mode        = 'RW',
        units       = 'cc',
    ))

    self.add(pr.RemoteVariable(
        name        = 'DcqcnAlphaG',
        description = 'Alpha EWMA weight. Stored as round((1-g)*1024). '
                      '1023 → g≈0.001 (slow). 512 → g=0.5 (fast).',
        offset      = 0x00C,
        bitSize     = 10,
        mode        = 'RW',
    ))

    self.add(pr.RemoteVariable(
        name        = 'DcqcnClampTgtRate',
        description = '1 = clamp target rate to current rate on CNP.',
        offset      = 0x010,
        bitSize     = 1,
        mode        = 'RW',
    ))

    self.add(pr.RemoteVariable(
        name        = 'DcqcnRai',
        description = 'Additive increase step (bytes/sec).',
        offset      = 0x014,
        bitSize     = 32,
        mode        = 'RW',
        units       = 'B/s',
    ))

    self.add(pr.RemoteVariable(
        name        = 'DcqcnRhai',
        description = 'Hyper-active increase step (bytes/sec).',
        offset      = 0x018,
        bitSize     = 32,
        mode        = 'RW',
        units       = 'B/s',
    ))

Initial Configuration
---------------------

``RoCEv2Server._start()`` writes the default DCQCN values before completing
the QP handshake:

.. code-block:: python

    async def _dcqcn_init(self, engine, clock_mhz: float = 250.0):
        cc = lambda us: round(us * clock_mhz)
        bps = lambda mbps: round(mbps * 1e6 / 8)

        engine.DcqcnRateIncInt.set(cc(5))
        engine.DcqcnRateDecInt.set(cc(4))
        engine.DcqcnAlphaUpdateInt.set(cc(55))
        engine.DcqcnAlphaG.set(1023)      # g ≈ 0.001
        engine.DcqcnClampTgtRate.set(0)
        engine.DcqcnRai.set(bps(50))
        engine.DcqcnRhai.set(bps(500))

Tuning Guidelines
------------------

These are general starting points; optimal values depend on your network
topology, switch buffer sizes, and target data rate.

* **Latency-sensitive, low-rate** (< 10 Gbps): increase ``RateIncInt`` to
  reduce oscillation; decrease ``AlphaG`` for slower alpha decay.
* **High-rate, bursty** (> 50 Gbps): decrease ``RateIncInt`` for faster
  recovery; increase ``R_hai`` for more aggressive ramp-up after congestion.
* **Lossless switch fabric** (PFC enabled): DCQCN still helps avoid head-of-
  line blocking; ``ClampTgtRate = 1`` can reduce overshoot.
* **Single flow, no competing traffic**: DCQCN parameters matter less; the
  defaults are conservative and safe.

For a detailed treatment of the parameter space, refer to the original
DCQCN paper (Zhu et al., SIGCOMM 2015) and the follow-up analysis by
Mittal et al. (2018).
