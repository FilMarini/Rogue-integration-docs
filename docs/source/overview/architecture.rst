Architecture
============

High-Level Diagram
------------------

The integration adds a new ``rogue.protocols.rocev2`` module that sits
alongside the existing UDP stack.  Both the RoCEv2 data traffic and the
SRP/UDP register traffic share the **same physical 10 GbE link** — they are
distinguished only by UDP port: RoCEv2 uses the mandatory port **4791**,
while SRP/UDP uses a separate application port (e.g. 8192)::

    ┌─────────────────────────────────────────────────────────┐
    │  FPGA                                                   │
    │                                                         │
    │  ┌──────────────┐    AXI-lite    ┌───────────────────┐  │
    │  │  User Logic  │◄──────────────►│  RoCEv2 Engine    │  │
    │  │  (Data Src)  │                │  (surf / Verilog) │  │
    │  └──────┬───────┘                │                   │  │
    │         │  RDMA WRITE            │  PD/MR/QP Manager │  │
    │         │  with-Immediate        │  DCQCN            │  │
    │         │  UDP port 4791         └────────┬──────────┘  │
    │         │                                 │ AXI-lite    │
    │         │                        ┌────────┴──────────┐  │
    │         │                        │  SRP/UDP Engine   │  │
    │         │                        │  (app UDP port)   │  │
    │         │                        └────────┬──────────┘  │
    │         │                                 │             │
    └─────────┼─────────────────────────────────┼─────────────┘
              │        10 GbE (shared link)      │
              │  RoCEv2 traffic (port 4791)       │  SRP/UDP traffic
              ▼                                  ▼
    ┌─────────────────────────────────────────────────────────┐
    │  HOST                                                   │
    │                                                         │
    │  ┌──────────────────────────────────────────────────┐   │
    │  │  pyrogue.protocols.RoCEv2Server                  │   │
    │  │                                                  │   │
    │  │  C++ Server (libibverbs)                         │   │
    │  │  ├─ RC QP + MR slab registration                 │   │
    │  │  └─ CQ polling thread                            │   │
    │  │                                                  │   │
    │  │  Python layer                                    │   │
    │  │  └─ _start(): metadata bus handshake via SRP     │   │
    │  └──────────────────┬───────────────────────────────┘   │
    │                     │ rogue Frame stream                 │
    │                     ▼                                    │
    │  ┌──────────────────────────────┐  ┌────────────────┐   │
    │  │  pyrogue Application Devices │  │  pyrogue       │   │
    │  │  StreamWriter / DataReceiver │  │  SRP/UDP       │   │
    │  └──────────────────────────────┘  └────────────────┘   │
    └─────────────────────────────────────────────────────────┘

Components
----------

rogue.protocols.rocev2 (C++)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The C++ layer provides the low-level RDMA plumbing:

``Server``
    The core class.  On construction it:

    1. Opens the RDMA device and allocates a **Protection Domain**.
    2. Registers a single contiguous **Memory Region** slab (size =
       ``rxQueueDepth × maxPayload``).
    3. Creates an RC **Queue Pair** and transitions it through
       RESET → INIT → RTR → RTS using the FPGA's QP number and GID
       (supplied after the Python-side handshake).
    4. Spawns a **CQ polling thread** that waits for
       ``IBV_WC_RECV_RDMA_WITH_IMM`` completions, extracts the channel ID
       from the 32-bit immediate value, wraps the payload in a
       ``rogue::interfaces::stream::Frame``, and calls ``sendFrame()``.

    Exposes getters so the Python layer can retrieve ``qp_num``, ``gid``,
    ``mr_addr``, and ``rkey`` after setup.

RoCEv2Server (Python / pyrogue)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A :class:`pyrogue.Device` subclass (``pyrogue.protocols.RoCEv2Server``) that:

* Owns the C++ ``Server`` instance.
* Contains the metadata bus encoding/decoding logic directly (there is no
  separate ``RoceEngine`` device — it is integrated into ``RoCEv2Server``).
* In ``_start()``, drives the metadata bus over SRP/UDP to configure the
  FPGA's PD → MR → QP → INIT → RTR → RTS, then tears everything down
  cleanly in ``_stop()``.

Memory Region Design
---------------------

Rather than registering individual buffers, a single **slab MR** is
registered once at startup::

    slab_size = rxQueueDepth × maxPayload
    slab_addr = ibv_reg_mr(pd, malloc(slab_size), slab_size,
                           IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_REMOTE_WRITE)

Buffers are sub-regions of the slab at fixed offsets::

    buffer[i].addr = slab_addr + i × maxPayload

This approach:

* Avoids expensive per-buffer ``ibv_reg_mr`` / ``ibv_dereg_mr`` calls.
* Gives the FPGA a simple linear address space it can round-robin through.
* Eliminates MR cache pressure on the NIC.

The FPGA WorkReqDispatcher uses ``addrWrapCount = rxQueueDepth`` to wrap
back to the base address after the last slot.

Immediate Value Format
-----------------------

Every RDMA WRITE-with-Immediate carries a 32-bit immediate value.
The format is defined on the host side (the FPGA has no predefined
format)::

    Bits [31:24]  — channel ID  (8 bits, 0–255)
    Bits [23: 0]  — reserved    (24 bits, must be zero)

The CQ polling thread extracts ``channel_id = (imm >> 24) & 0xFF``
and routes the frame to the corresponding application port.

SSI Frame Framing
------------------

The rogue stream interface uses **SSI (SLAC Streaming Interface)** sideband
signals.  Since each RDMA WRITE is an atomic complete frame, the C++ server
hardcodes:

* ``firstUser = 0x2``  (SOF — Start Of Frame)
* ``lastUser``          derived from the FPGA (or set to 0)

This matches the behaviour of the existing UDP/RSSI path so downstream
consumers see identical frames regardless of transport.
