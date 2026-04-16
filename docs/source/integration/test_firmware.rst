Test Firmware Components
========================

The test firmware includes two VHDL modules that sit on top of the RoCEv2
engine to drive and monitor RDMA WRITE traffic:

* **WorkReqDispatcher** — generates a continuous stream of RDMA WRITE work
  requests targeting the host MR.
* **WorkCompChecker** — consumes the RoCEv2 engine's work completion
  notifications and counts successful vs unsuccessful ACKs.

Both modules expose AXI-lite registers so they can be controlled and
monitored from pyrogue over the SRP/UDP path.

.. note::
   These modules are part of the **test firmware** and are not required in
   production designs.  In production, the FPGA user logic produces AXI-Stream
   frames that are fed into the RoCEv2 engine directly; the WorkReqDispatcher
   is only used in loopback/test configurations.

----

WorkReqDispatcher
-----------------

The WorkReqDispatcher is the FPGA-side module that generates RDMA WRITE
work requests.  It reads a frame slot address from a round-robin counter,
packages it into a ``RoceWorkReqMasterType`` record, and submits it to the
RoCEv2 engine.

Generics
~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Generic
     - Default
     - Description
   * - ``TPD_G``
     - 1 ns
     - Propagation delay (simulation only)
   * - ``RST_ASYNC_G``
     - false
     - Use asynchronous reset
   * - ``DISPATCH_COUNTER_BITS_G``
     - 24
     - Width of the dispatch counter (max dispatches before wrap =
       ``2^DISPATCH_COUNTER_BITS_G``)

Ports
~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 10 65

   * - Port
     - Dir
     - Description
   * - ``RoceClk``
     - in
     - RoCEv2 engine clock
   * - ``RoceRst``
     - in
     - Synchronous (or async if ``RST_ASYNC_G``) reset, active high
   * - ``workReqMaster_o``
     - out
     - RDMA work request stream to the RoCEv2 engine
   * - ``workReqSlave_i``
     - in
     - Back-pressure / ready signal from the RoCEv2 engine
   * - ``startingDispatch_o``
     - out
     - Asserted when dispatch is active; connected to
       ``WorkCompChecker.startingDispatch``
   * - ``axilReadMaster``
     - in
     - AXI-lite read channel
   * - ``axilReadSlave``
     - out
     - AXI-lite read response
   * - ``axilWriteMaster``
     - in
     - AXI-lite write channel
   * - ``axilWriteSlave``
     - out
     - AXI-lite write response

AXI-lite Register Map
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 14 18 10 58

   * - Offset
     - Bits
     - R/W
     - Description
   * - ``0xF00``
     - ``[0]``
     - RW
     - **startDispatching** — write ``1`` to start issuing work requests;
       write ``0`` to stop.  New requests stop being submitted immediately;
       in-flight requests complete normally.
   * - ``0xF00``
     - ``[24:1]``
     - RO
     - **dispatchCounter** — running count of work requests submitted since
       ``startDispatching`` was last asserted.  Wraps at
       ``2^DISPATCH_COUNTER_BITS_G``.
   * - ``0xF04``
     - ``[31:0]``
     - RW
     - **len** — byte length of each RDMA WRITE (= frame size =
       ``maxPayload``).  Must match the ``FrameLen`` programmed on the host.
   * - ``0xF08``
     - ``[31:0]``
     - RW
     - **rKey** — remote key of the host MR.  Copied from
       ``server.getMrRkey()``.
   * - ``0xF0C``
     - ``[31:0]``
     - RW
     - **lKey** — local key of the FPGA's MR (returned by the MR
       allocation metadata response).
   * - ``0xF10``
     - ``[23:0]``
     - RW
     - **sQpn** — source QP number (FPGA's QP number, from QP create
       response).
   * - ``0xF14``
     - ``[24:0]``
     - RW
     - **dQpn** — destination QP number (host QP number, from
       ``server.getQpNum()``).
   * - ``0xF18``
     - ``[63:0]``
     - RW
     - **rAddr** — base virtual address of the host MR slab (64-bit).
       Low 32 bits at ``0xF18``, high 32 bits at ``0xF1C``.
       Copied from ``server.getMrAddr()``.  When this register is written
       with a new value, ``addrCount`` is automatically reset to 0.
   * - ``0xF20``
     - ``[31:0]``
     - RW
     - **addrWrapCount** — number of frame slots before the address wraps
       back to ``rAddr``.  Set to ``rxQueueDepth`` on the host.
       The dispatcher computes the current slot address as
       ``rAddr + (addrCount mod addrWrapCount) × len``.

.. note::
   ``rAddr`` is 64 bits and spans two 32-bit AXI-lite words at ``0xF18``
   (low) and ``0xF1C`` (high).  ``addrWrapCount`` therefore starts at
   ``0xF20``, the next available 32-bit address.

Address Wrapping Logic
~~~~~~~~~~~~~~~~~~~~~~

The dispatcher maintains an internal ``addrCount`` (slot index) that is
separate from ``dispatchCounter``::

    current_addr = rAddr + (addrCount mod addrWrapCount) × len

    After each accepted work request:
        addrCount ← addrCount + 1
        if addrCount == addrWrapCount:
            addrCount ← 0

This gives a simple round-robin over the ``rxQueueDepth`` host MR slots,
matching the slab layout registered by the C++ ``Server``.

``addrCount`` persists across multiple dispatch bursts within the same
session (i.e. ``startDispatching`` can be toggled without resetting the
slot pointer).  It is only reset when ``rAddr`` is written with a new
value, which happens when the host restarts and registers a new MR.

Immediate Value
~~~~~~~~~~~~~~~

Each work request sets the 32-bit RDMA immediate value to::

    imm_data[31:24] = channelId   (configured separately)
    imm_data[23:0]  = 0           (reserved)

This allows the host CQ polling thread to route frames to the correct
application channel.

----

WorkCompChecker
---------------

The WorkCompChecker consumes the ``RoceWorkCompMasterType`` stream from the
RoCEv2 engine and tallies successful versus unsuccessful completions.  Each
RDMA WRITE generates one work completion entry; the ``status`` field is
``"00000"`` (5 bits) on success and non-zero on any error.

Generics
~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Generic
     - Default
     - Description
   * - ``TPD_G``
     - 1 ns
     - Propagation delay (simulation only)
   * - ``RST_ASYNC_G``
     - false
     - Use asynchronous reset
   * - ``DISPATCH_COUNTER_BITS_G``
     - 24
     - Width of the success/unsuccess counters (same as WorkReqDispatcher)

Ports
~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 10 65

   * - Port
     - Dir
     - Description
   * - ``RoceClk``
     - in
     - RoCEv2 engine clock
   * - ``RoceRst``
     - in
     - Reset, active high
   * - ``WorkCompMaster``
     - in
     - Work completion stream from the RoCEv2 engine
   * - ``WorkCompSlave``
     - out
     - Ready signal back to the RoCEv2 engine
   * - ``startingDispatch``
     - in
     - Driven by ``WorkReqDispatcher.startingDispatch_o``.
       Reserved for future gating logic.
   * - ``axilReadMaster``
     - in
     - AXI-lite read channel
   * - ``axilReadSlave``
     - out
     - AXI-lite read response
   * - ``axilWriteMaster``
     - in
     - AXI-lite write channel
   * - ``axilWriteSlave``
     - out
     - AXI-lite write response

AXI-lite Register Map
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 14 18 10 58

   * - Offset
     - Bits
     - R/W
     - Description
   * - ``0xF00``
     - ``[23:0]``
     - RO
     - **successCounter** — number of work completions received with
       ``status = "00000"`` (success) since last reset.
   * - ``0xF04``
     - ``[23:0]``
     - RO
     - **unsuccessCounter** — number of work completions received with
       ``status ≠ "00000"`` (any error) since last reset.
   * - ``0xF08``
     - ``[0]``
     - RW
     - **resetCounters** — write ``1`` to clear both counters to zero.
       The counters reset on the same clock edge as the write; no pulse
       is required (the register is level-sensitive).

.. note::
   The counter width is ``DISPATCH_COUNTER_BITS_G`` bits (default 24).
   At 24 bits the counters wrap at 16,777,216 completions.  For
   long-running tests, read and accumulate in software before overflow.

State Machine
~~~~~~~~~~~~~

The checker has a two-state FSM::

    st0_idle
      │  WorkCompMaster.valid = '1'
      ▼
    st1_received
      │  latch status field
      │
      ├─ status = "00000"  →  successCounter++   →  st0_idle
      └─ status ≠ "00000"  →  unsuccessCounter++ →  st0_idle

The ``ready`` signal is asserted only in ``st0_idle`` when a valid
completion is present, ensuring completions are consumed one at a time
with no loss.

Status Field Encoding
~~~~~~~~~~~~~~~~~~~~~

The 5-bit ``status`` field mirrors the IB work completion status codes:

.. list-table::
   :header-rows: 1
   :widths: 12 88

   * - Value
     - Meaning
   * - ``00000``
     - **Success** — RDMA WRITE acknowledged by remote NIC
   * - ``00001``
     - Local length error
   * - ``00010``
     - Local QP operation error
   * - ``00011``
     - Local EE context operation error
   * - ``00100``
     - Local protection error (rkey/addr invalid)
   * - ``00101``
     - Work request flushed (QP in error state)
   * - ``00110``
     - Memory window bind error
   * - ``01000``
     - Bad response error (unexpected packet)
   * - ``01001``
     - Local access error
   * - ``01010``
     - Remote invalid request error
   * - ``01011``
     - Remote access error (remote NIC rejected rkey)
   * - ``01100``
     - Remote operation error
   * - ``01101``
     - Transport retry counter exceeded
   * - ``01110``
     - RNR retry counter exceeded

In normal operation with a working RDMA link, only ``00000`` should appear.
Persistent non-zero status codes indicate a configuration error (wrong
``rKey``, wrong ``rAddr``, QP not in RTS) or a network-level issue
(see :doc:`../appendix/troubleshooting`).

----

Relationship Between the Two Modules
--------------------------------------

The two modules are wired together in the test firmware top level::

    WorkReqDispatcher
        │  startingDispatch_o ──────────────────────────────────┐
        │  workReqMaster_o  ─────────────────────────────────┐  │
        │                                                     │  │
        │                                                RoCEv2 Engine
        │                                                     │  │
        │                                    workCompMaster ──┘  │
        ▼                                                         │
    WorkCompChecker ◄────────────────── startingDispatch ─────────┘

For every work request that ``WorkReqDispatcher`` submits, the RoCEv2 engine
will eventually generate one work completion entry on the ``workCompMaster``
stream.  In steady state::

    successCounter + unsuccessCounter ≈ dispatchCounter

The difference is the number of in-flight requests that have been submitted
but not yet acknowledged.

pyrogue Variables (test firmware)
-----------------------------------

In the test firmware these registers are exposed as two pyrogue devices:

.. code-block:: python

    self.add(pyrogue.protocols.WorkReqDispatcher(
        name   = 'WorkReqDispatcher',
        memBase= srp,
        offset = 0x0000_B000,    # firmware-specific base address
    ))

    self.add(pyrogue.protocols.WorkCompChecker(
        name   = 'WorkCompChecker',
        memBase= srp,
        offset = 0x0000_C000,
    ))

After ``root.start()`` and the RDMA handshake, start a test burst:

.. code-block:: python

    wrd = root.WorkReqDispatcher
    wcc = root.WorkCompChecker

    # Program dispatch parameters (normally done by RoCEv2Server._start())
    wrd.RAddr.set(root.Rdma.MrAddr.get())
    wrd.RKey.set(root.Rdma.MrRkey.get())
    wrd.AddrWrapCount.set(256)      # rxQueueDepth
    wrd.Len.set(8192)               # maxPayload

    # Reset counters and start
    wcc.ResetCounters.set(1)
    wcc.ResetCounters.set(0)
    wrd.StartDispatching.set(1)

    # ... wait ...
    wrd.StartDispatching.set(0)

    ok  = wcc.SuccessCounter.get()
    err = wcc.UnsuccessCounter.get()
    sent = wrd.DispatchCounter.get()

    print(f"Sent: {sent}  OK: {ok}  Errors: {err}  "
          f"Loss: {sent - ok - err} (in-flight)")
