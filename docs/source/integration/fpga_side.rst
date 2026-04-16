FPGA-Side Setup
===============

The FPGA firmware contains a BSV-based RoCEv2 engine that manages its own
RDMA resources internally.  This page describes the FPGA perspective.

Internal Resource Manager
--------------------------

The RoCEv2 engine implements a mini resource manager supporting:

* Up to ``MAX_PD = 8`` Protection Domains.
* Up to ``MAX_MR_PER_PD`` Memory Regions per PD.
* Queue Pairs, with configurable capacity.

All resources are allocated and configured by the host through the
**Metadata Bus** (see :doc:`../metadata/overview`) via AXI-lite writes.

The FPGA firmware does **not** use ``libibverbs``.  It implements its own
stripped-down RDMA verbs layer in hardware.

Data Path
---------

.. seealso::
   The RoCEv2 engine does not take an AXI-Stream directly.  It uses an
   internal DMA read interface to fetch payload data from FPGA-side memory
   when processing work requests.  See :doc:`dma_interface` for the full
   ``RoceDmaReadReq/Resp`` record definitions and the ``TestDmaServer``
   description.

Once the QP is in RTS state, the FPGA data path is::

    User Logic
        │  (AXI-Stream frames)
        ▼
    WorkReqDispatcher
        │  Generates RDMA WRITE Work Requests
        │  dest_addr = MrBaseAddr + (slot_counter mod addrWrapCount) × frameLen
        │  imm_data  = (channel_id << 24)
        ▼
    RoCEv2 Engine
        │  Packetizes into RoCEv2 / IB packets
        │  Applies DCQCN rate limiting
        ▼
    100GbE MAC / PHY

WorkReqDispatcher Register Map
--------------------------------

.. seealso::
   For the full WorkReqDispatcher and WorkCompChecker documentation,
   including generics, ports, state machines and pyrogue usage examples,
   see :doc:`test_firmware`.

The WorkReqDispatcher is a firmware module that sits between user logic and
the RoCEv2 engine.  It is configured via AXI-lite:

.. list-table::
   :header-rows: 1
   :widths: 15 15 15 55

   * - Offset
     - Bits
     - Name
     - Description
   * - ``0xF10``
     - [63:0]
     - ``RAddr``
     - Base virtual address of the host MR (64-bit).  Low word at
       ``0xF10``, high word at ``0xF14``.
   * - ``0xF18``
     - [31:0]
     - ``RKey``
     - Remote key of the host MR.
   * - ``0xF20``
     - [31:0]
     - ``AddrWrapCount``
     - Number of slots before wrapping back to ``RAddr``.  Set to
       ``rxQueueDepth`` on the host.
   * - ``0xF24``
     - [31:0]
     - ``FrameLen``
     - Length of each frame slot in bytes (= ``maxPayload``).
   * - ``0xF28``
     - [7:0]
     - ``ChannelId``
     - Channel ID placed in bits [31:24] of the RDMA immediate value.

Address Wrap Logic
~~~~~~~~~~~~~~~~~~

The dispatcher cycles through frame slots::

    current_addr = RAddr + (counter mod AddrWrapCount) × FrameLen
    counter += 1

When ``counter == AddrWrapCount``, it resets to 0.  This gives the host a
predictable round-robin receive buffer that matches the slab MR layout.

FPGA GID
---------

The FPGA GID is derived from the FPGA IP address using IPv4-mapped IPv6
format.  For FPGA IP ``192.168.1.10``::

    GID = ::ffff:192.168.1.10
        = 0000:0000:0000:0000:0000:ffff:c0a8:010a

The host uses this same derivation to fill in the ``ah_attr.grh.dgid`` field
when transitioning the host QP to RTR (see :doc:`host_side`).

The FPGA reads its own GID from its configuration registers; the host never
needs to query the FPGA for its GID explicitly.

Firmware Configuration Summary
--------------------------------

The firmware registers that must be written by the host before data flow
begins are:

1. **Metadata bus sequence** (via ``RoceEngine`` AXI-lite):

   * PD allocate → get ``pdHandler``
   * MR allocate → get ``lkey`` (and internally store ``rkey``, ``addr``)
   * QP create → get ``qpn``
   * QP INIT
   * QP RTR (supply host ``qp_num``, ``gid``, ``psn``)
   * QP RTS (supply ``retry_cnt``, ``rnr_retry``, ``timeout``)

2. **WorkReqDispatcher registers** (via SRP/UDP):

   * ``RAddr``, ``RKey``, ``AddrWrapCount``, ``FrameLen``, ``ChannelId``

3. **DCQCN registers** (via SRP/UDP, optional tuning):

   * See :doc:`../dcqcn/registers`.

All of steps 1 and 2 are performed automatically by
``RoCEv2Server._start()`` (see :doc:`connection_flow`).
