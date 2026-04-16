Connection Lifecycle
====================

This page describes how the rogue ``RoCEv2Server`` establishes, uses, and
tears down the RDMA connection over its full lifetime — from the first
``root.start()`` call through ZMQ server restarts.

Overview
--------

The RDMA connection is a **stateful RC (Reliable Connected) Queue Pair**.
Both endpoints — the host NIC and the FPGA engine — must agree on QP
parameters, and both must be in the ``RTS`` state before data can flow.

Because the FPGA engine retains its internal PD, MR, and QP state across
software restarts (it is only reset on FPGA power-cycle or firmware reload),
the host must handle two scenarios on startup:

1. **Fresh start** — FPGA is in a clean state; full PD → MR → QP → INIT →
   RTR → RTS sequence is needed.
2. **Restart after crash/stop** — FPGA QP may still be in ``RTS`` or
   ``RTS`` with a now-stale host QP.  The host must tear down the old QP
   before setting up a new one.

Startup Sequence
----------------

This is the sequence executed by ``RoCEv2Server._start()`` every time
``root.start()`` is called (see also :doc:`connection_flow`):

.. code-block:: text

    ┌─────────────────────────────────────────────────────────────────┐
    │ 1. C++ Server construction                                      │
    │    • ibv_open_device()                                          │
    │    • ibv_alloc_pd()                                             │
    │    • ibv_reg_mr()  →  new MR slab (new addr + new rkey)        │
    │    • ibv_create_qp() RESET → INIT  →  new host_qp_num          │
    └─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ 2. Teardown probe (Python, via metadata bus)                    │
    │    • REQ_QP_QUERY with the last-known FPGA QPN                  │
    │    • If QP found in RTS/RTR/INIT:                               │
    │        – REQ_QP_MODIFY → IBV_QPS_ERR                           │
    │        – REQ_QP_DESTROY                                         │
    │    • If QP not found or already in RESET:  skip teardown        │
    │    • Teardown errors are non-fatal — logged as warnings          │
    └─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ 3. Full connection setup (Python, via metadata bus)             │
    │    • PD alloc  → pdHandler                                      │
    │    • MR alloc  → lkey  (supply new host addr + rkey)            │
    │    • QP create → fpga_qpn                                       │
    │    • QP INIT                                                     │
    │    • QP RTR    (supply new host_qp_num, host_gid, host_rq_psn) │
    │    • Host QP: INIT → RTR (using fpga_qpn, fpga_gid)            │
    │    • QP RTS    (supply retry_cnt, rnr_retry, timeout)           │
    │    • Host QP: RTR → RTS                                         │
    └─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ 4. WorkReqDispatcher programming (Python, via SRP/UDP)          │
    │    • RAddr ← new host MR addr                                   │
    │    • RKey  ← new host MR rkey                                   │
    │    • AddrWrapCount ← rxQueueDepth                               │
    │    • FrameLen ← maxPayload                                       │
    └─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ 5. DCQCN initial configuration (Python, via SRP/UDP)            │
    └─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ 6. CQ polling thread started (C++)                              │
    │    ConnectionState ← 'Connected'                                │
    └─────────────────────────────────────────────────────────────────┘

After step 6, data flows: FPGA WRITEs arrive at the host MR, the CQ
polling thread delivers frames to the rogue pipeline.

Why a New MR on Every Restart
------------------------------

Every time ``root.start()`` is called, the C++ ``Server`` constructor runs
from scratch and calls ``ibv_reg_mr()`` again.  This means:

* A **new virtual address** is assigned to the MR slab.
* A **new rkey** is issued by the host NIC.

The FPGA must be given the new address and rkey on every startup — it cannot
reuse the previous values because they are no longer valid.  This is why
step 3 always performs a full MR allocation (not a modify) and why step 4
always rewrites the WorkReqDispatcher registers.

.. important::
   When ``rAddr`` is written to the WorkReqDispatcher with a new value,
   the FPGA's internal ``addrCount`` is automatically reset to 0.  This
   prevents stale slot offsets from a previous session being applied to
   a new MR base address.

Teardown Probe Details
-----------------------

The teardown probe in step 2 uses the last FPGA QPN stored in the Python
``RoCEv2Server`` instance from the previous session.  Since the variable is
in memory, it is lost when the ZMQ server process exits.

On the very first run (or after an FPGA reset), the stored QPN is 0.  The
probe sends ``REQ_QP_QUERY`` with QPN=0; if the FPGA returns "not found" or
"already in RESET", teardown is skipped and the fresh setup proceeds
immediately.

On a restart, the stored QPN is the one assigned in the previous session.
The probe queries its state:

* **RTS / RTR / INIT** — the old QP is still live.  Teardown is mandatory:
  the old QP holds a reference to a now-invalid host MR (old rkey/addr).
  Leaving it in RTS would cause the FPGA to send WRITEs to stale addresses,
  which the host NIC would reject with ``IBV_WC_REM_ACCESS_ERR``.
* **ERR** — a previous teardown was partially completed.  Send
  ``REQ_QP_DESTROY`` only.
* **RESET** — fully torn down.  Skip teardown.
* **Query failure** — FPGA state unknown (e.g. firmware reloaded and QPN
  reassigned).  Log a warning and proceed; the new PD alloc will succeed
  if the firmware is in a clean state.

Shutdown Sequence
-----------------

When ``root.stop()`` is called (or when the ZMQ server process exits cleanly
via ``with root as hw``), the following happens:

.. code-block:: text

    ┌─────────────────────────────────────────────────────────────────┐
    │ 1. CQ polling thread stopped (C++)                              │
    │    ConnectionState ← 'Disconnecting'                            │
    └─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ 2. FPGA QP graceful teardown (Python, via metadata bus)         │
    │    • REQ_QP_MODIFY → IBV_QPS_ERR   (drain in-flight WRITEs)    │
    │    • REQ_QP_DESTROY                                             │
    │    (PD and MR are left allocated — they are freed on FPGA       │
    │     power-cycle.  A fresh alloc is always done on the next      │
    │     startup, so leaking them is harmless within a session.)     │
    └─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ 3. Host libibverbs resources freed (C++ destructor)             │
    │    • ibv_destroy_qp()                                           │
    │    • ibv_dereg_mr()                                             │
    │    • ibv_destroy_cq()                                           │
    │    • ibv_dealloc_pd()                                           │
    │    • ibv_close_device()                                         │
    │    ConnectionState ← 'Disconnected'                             │
    └─────────────────────────────────────────────────────────────────┘

.. note::
   Step 2 is best-effort.  If the ZMQ server is killed with ``SIGKILL``
   or crashes, the teardown does not run and the FPGA QP is left in
   whatever state it was in.  The startup probe in the next session
   handles this case.

   The host-side resources in step 3 are always freed by the C++
   destructor (RAII), even if the FPGA teardown failed.

Restart Scenario Walkthrough
-----------------------------

::

    Session 1:
        startZmq.py starts
        → fresh FPGA: teardown probe finds nothing
        → full handshake: fpga_qpn = 0x0042, host_qp_num = 0xABC1
        → MR at addr=0x7f1234000000, rkey=0x11223344
        → data flows

        [user Ctrl-C]
        → graceful shutdown: QP 0x0042 → ERR → DESTROY
        → host MR deregistered

    Session 2 (restart):
        startZmq.py starts
        → teardown probe: query QP 0x0042
          → FPGA returns RESET (was destroyed in session 1)
          → skip teardown
        → full handshake: fpga_qpn = 0x0043 (new), host_qp_num = 0xABC2 (new)
        → MR at addr=0x7f5678000000 (new), rkey=0xAABBCCDD (new)
        → WorkReqDispatcher RAddr/RKey updated, addrCount reset to 0
        → data flows

    Session 3 (crash recovery):
        startZmq.py starts (previous session crashed, no teardown ran)
        → teardown probe: query QP 0x0043
          → FPGA returns RTS (still running, pointing at stale MR)
          → send REQ_QP_MODIFY → ERR
          → send REQ_QP_DESTROY
        → full handshake: fpga_qpn = 0x0044 (new)
        → MR at addr=0x7f9ABC000000 (new), rkey=0x55667788 (new)
        → data flows

ConnectionState Variable
-------------------------

The ``ConnectionState`` pyrogue variable (on ``RoCEv2Server``) reflects the
current lifecycle phase and can be polled by application scripts:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Value
     - Meaning
   * - ``'Disconnected'``
     - Initial state; ``root.start()`` has not completed yet, or
       ``root.stop()`` has completed.
   * - ``'Connecting'``
     - ``_start()`` is in progress (handshake running).
   * - ``'Connected'``
     - Handshake complete, CQ polling thread running, data flowing.
   * - ``'Disconnecting'``
     - ``_stop()`` in progress.
   * - ``'Error'``
     - A fatal error occurred during connection setup.  Check logs.

Example check in an application script:

.. code-block:: python

    import pyrogue.interfaces

    with pyrogue.interfaces.VirtualClient(addr='localhost', port=9099) as c:
        state = c.root.Rdma.ConnectionState.get()
        if state != 'Connected':
            raise RuntimeError(f'RoCEv2 not ready: state={state}')

        print('Host QPN :', hex(c.root.Rdma.HostQpNum.get()))
        print('Host GID :', c.root.Rdma.HostGid.get())
        print('MR addr  :', hex(c.root.Rdma.MrAddr.get()))
        print('MR rkey  :', hex(c.root.Rdma.MrRkey.get()))
        print('FPGA QPN :', hex(c.root.Rdma.FpgaQpn.get()))
        print('FPGA lkey:', hex(c.root.Rdma.FpgaLkey.get()))
