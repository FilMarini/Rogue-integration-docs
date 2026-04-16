Connection Lifecycle
====================

This page describes how the rogue ``RoCEv2Server`` establishes, uses, and
tears down the RDMA connection over its full lifetime — from the first
``root.start()`` call through ZMQ server restarts.

Design Principle
----------------

The connection lifecycle follows a simple **destroy-and-recreate** model:

* On ``_stop()`` (ZMQ server exit, ``Ctrl-C``, or ``root.stop()``):
  the FPGA PD, MR, and QP are **fully destroyed** via the metadata bus.
  Host libibverbs resources are freed.

* On ``_start()`` (every ZMQ server launch):
  a fresh PD, MR, and QP are created from scratch.  The host registers a
  new MR slab (new address, new rkey) and completes a full handshake.

This means there is **no teardown probe** and no attempt to reuse state
from a previous session.  Every startup begins from a clean FPGA state.

Startup Sequence
----------------

Executed by ``RoCEv2Server._start()`` on every ``root.start()``:

.. code-block:: text

    ┌─────────────────────────────────────────────────────────────────┐
    │ 1. C++ Server construction                                      │
    │    • ibv_open_device()                                          │
    │    • ibv_alloc_pd()                                             │
    │    • ibv_reg_mr()  →  new MR slab (new addr + new rkey)        │
    │    • ibv_create_qp()  RESET → INIT  →  new host_qp_num         │
    └─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ 2. FPGA resource allocation (Python, via metadata bus / SRP)    │
    │    • PD alloc  → pdHandler                                      │
    │    • MR alloc  → lkey  (supply new host addr + rkey)            │
    │    • QP create → fpga_qpn                                       │
    │    • QP INIT                                                    │
    │    • QP RTR    (supply host_qp_num, host_gid, host_rq_psn)     │
    │    • Host QP: INIT → RTR  (using fpga_qpn, fpga_gid)           │
    │    • QP RTS    (supply retry_cnt, rnr_retry, timeout)           │
    │    • Host QP: RTR → RTS                                         │
    └─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ 3. WorkReqDispatcher programming (Python, via SRP/UDP)          │
    │    • RAddr ← new host MR addr                                   │
    │    • RKey  ← new host MR rkey                                   │
    │    • AddrWrapCount ← rxQueueDepth                               │
    │    • FrameLen ← maxPayload                                      │
    └─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ 4. DCQCN initial configuration (Python, via SRP/UDP)            │
    └─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ 5. CQ polling thread started (C++)                              │
    │    ConnectionState ← 'Connected'                                │
    └─────────────────────────────────────────────────────────────────┘

Why a New MR on Every Startup
------------------------------

Every ``_start()`` call registers a new MR slab via ``ibv_reg_mr()``,
which assigns a new virtual address and a new rkey.  The FPGA must always
receive the current values — it cannot reuse addresses from a previous
session because the host has deallocated them.

This is why step 2 always performs a full MR allocation (not a modify),
and why step 3 always rewrites the WorkReqDispatcher registers.

When ``RAddr`` is written to the WorkReqDispatcher with a new value, the
FPGA's internal ``addrCount`` is automatically reset to 0, preventing
stale slot offsets from a previous session being applied to the new base
address.

Shutdown Sequence
-----------------

Executed by ``RoCEv2Server._stop()`` on ``root.stop()`` or process exit:

.. code-block:: text

    ┌─────────────────────────────────────────────────────────────────┐
    │ 1. CQ polling thread stopped (C++)                              │
    │    ConnectionState ← 'Disconnecting'                            │
    └─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ 2. FPGA resource teardown (Python, via metadata bus / SRP)      │
    │    • QP → IBV_QPS_ERR  (drain any in-flight WRITEs)            │
    │    • QP destroy                                                 │
    │    • MR free                                                    │
    │    • PD free                                                    │
    └─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ 3. Host libibverbs resources freed (C++ destructor / RAII)      │
    │    • ibv_destroy_qp()                                           │
    │    • ibv_dereg_mr()                                             │
    │    • ibv_destroy_cq()                                           │
    │    • ibv_dealloc_pd()                                           │
    │    • ibv_close_device()                                         │
    │    ConnectionState ← 'Disconnected'                             │
    └─────────────────────────────────────────────────────────────────┘

.. note::
   The FPGA teardown in step 2 is best-effort.  If the process is killed
   with ``SIGKILL`` or crashes hard, the metadata bus teardown does not
   run and the FPGA is left with a stale QP.

   In this case, the FPGA firmware must be reset (or the FPGA power-cycled)
   before the next ``_start()`` — otherwise the PD alloc in step 2 of the
   next startup will fail because ``MAX_PD = 1`` is already occupied.

   For a graceful exit, always use ``Ctrl-C`` or ``SIGTERM`` so that the
   pyrogue shutdown hooks run.

MAX_PD = 1 Constraint
----------------------

The FPGA RoCEv2 engine supports only **one Protection Domain** at a time
(``MAX_PD = 1``).  This means:

* Only one active RDMA connection is possible at any time.
* If ``_stop()`` did not run (crash/kill), the next ``_start()`` will
  fail at the PD alloc step with a failure response from the FPGA.
* Recovery requires an FPGA firmware reset.

ConnectionState Variable
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Value
     - Meaning
   * - ``'Disconnected'``
     - Initial state or after ``_stop()`` has completed.
   * - ``'Connecting'``
     - ``_start()`` is in progress.
   * - ``'Connected'``
     - Handshake complete, CQ polling thread running, data flowing.
   * - ``'Disconnecting'``
     - ``_stop()`` in progress.
   * - ``'Error'``
     - A fatal error occurred.  Check logs.
