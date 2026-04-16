FPGA DMA Interface
==================

The RoCEv2 engine does **not** accept an AXI-Stream directly.  Instead, it
works as an RDMA **initiator**: the user logic submits a *work request*
describing what to send, and the engine issues an internal DMA read to fetch
the payload from FPGA-side memory before packetising it into RoCEv2 frames
and sending them over the wire.

This page describes the DMA read request/response interface and the
``DmaTestPatternServer`` module used in the test firmware to serve synthetic
data.

Why a DMA Interface?
--------------------

An RDMA WRITE-with-Immediate operation requires the sender (FPGA) to:

1. Know the **destination** in host memory — the ``rAddr`` and ``rKey``
   configured via the WorkReqDispatcher (see :doc:`test_firmware`).
2. Know the **source** in FPGA-side memory — a ``startAddr`` and ``len``
   from the work request.
3. **Fetch the payload** from FPGA memory before packetising.

Step 3 is done through the DMA read interface.  The RoCEv2 engine issues one
or more ``RoceDmaReadReq`` beats, each covering up to one packet's worth of
data, and the DMA server (user logic or ``DmaTestPatternServer``) responds
with the corresponding payload.

Data Flow
---------

::

    User Logic (or DmaTestPatternServer)
         │  DmaReadResp ──────────────────────────────────────────┐
         │                                                         │
    WorkReqDispatcher                                         RoCEv2 Engine
         │  WorkReqMaster (rAddr, rKey, len, startAddr, ...)       │
         └──────────────────────────────────────────────────────► │
                                                                   │  DmaReadReq
                                                                   └──────────────►
                                                               (startAddr, len, ...)
                                                                   │
                                                     DmaTestPatternServer / user logic
                                                                   │  DmaReadResp
                                                                   │  (data beats)
                                                                   ◄──────────────

The WorkReqDispatcher submits a work request that tells the engine:
*"perform an RDMA WRITE of ``len`` bytes from FPGA address ``startAddr``
into host MR at ``rAddr`` using ``rKey``".*

For each work request, the engine breaks it into MTU-sized DMA read
requests and reassembles the responses into RoCEv2 packets.

DMA Read Request Record
-----------------------

.. code-block:: vhdl

    type RoceDmaReadReqMasterType is record
        valid     : sl;
        initiator : slv(3 downto 0);
        sQpn      : slv(23 downto 0);
        wrId      : slv(63 downto 0);
        startAddr : slv(63 downto 0);
        len       : slv(12 downto 0);
        mrIdx     : sl;
    end record RoceDmaReadReqMasterType;

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Width
     - Description
   * - ``valid``
     - 1
     - Assert when a request is ready.
   * - ``initiator``
     - 4
     - Internal RoCEv2 engine initiator tag.  Must be echoed back in
       the response so the engine can match requests to responses.
   * - ``sQpn``
     - 24
     - Source QP number — identifies which QP issued this request.
       Must be echoed in the response.
   * - ``wrId``
     - 64
     - Work Request ID — opaque identifier from the original work
       request.  Echoed in the DMA response and in the work completion
       record.
   * - ``startAddr``
     - 64
     - Start address in FPGA-side memory of the data to fetch.
       In ``DmaTestPatternServer`` this field is received but the byte
       pattern is driven by the persistent global counter, not by
       ``startAddr``.
   * - ``len``
     - 13
     - Number of bytes requested in this transaction (max 8192).
   * - ``mrIdx``
     - 1
     - Memory Region index selector (0 or 1).

The slave side carries only a ``ready`` handshake signal:

.. code-block:: vhdl

    type RoceDmaReadReqSlaveType is record
        ready : sl;
    end record RoceDmaReadReqSlaveType;

DMA Read Response Record
------------------------

.. code-block:: vhdl

    type RoceDmaReadRespMasterType is record
        valid      : sl;
        initiator  : slv(3 downto 0);
        sQpn       : slv(23 downto 0);
        wrId       : slv(63 downto 0);
        isRespErr  : sl;
        dataStream : slv(289 downto 0);
    end record RoceDmaReadRespMasterType;

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Width
     - Description
   * - ``valid``
     - 1
     - Assert when this response beat is valid.
   * - ``initiator``
     - 4
     - Echoed from the request.
   * - ``sQpn``
     - 24
     - Source QP number — echoed from the request.
   * - ``wrId``
     - 64
     - Work Request ID — echoed from the request.
   * - ``isRespErr``
     - 1
     - Set to ``1`` to indicate a DMA read error.  The engine will
       mark the corresponding work completion as failed.
   * - ``dataStream``
     - 290
     - Payload data beat.  Layout (LSB to MSB):

       .. code-block::

           [255:0]   — 32 bytes of payload data
           [287:256] — tKeep byte-enable (32 bits, 1 bit per byte)
           [288]     — isFirst (SSI SOF flag for first beat)
           [289]     — isLast  (last beat of this response)

Each DMA read request generates exactly one response transaction, potentially
spanning multiple 32-byte beats.  The final beat has ``isLast = '1'``.
The request/response pair is matched by ``(initiator, sQpn, wrId)``; all
three must be echoed unchanged.

.. code-block:: vhdl

    type RoceDmaReadRespSlaveType is record
        ready : sl;
    end record RoceDmaReadRespSlaveType;

----

DmaTestPatternServer
---------------------

``DmaTestPatternServer`` (entity ``DmaTestPatternServer``, file
``DmaTestPatternServer.vhd``) is a synthesisable VHDL module that responds
to DMA read requests with a synthetic incrementing byte pattern.  It is used
in the test firmware (``Simple-10GbE-RUDP-KCU105-Example``) when there is
no real user data source.

Internal FIFO
~~~~~~~~~~~~~

Incoming DMA requests are queued through an ``AxiStreamFifoV2`` instance
(depth 16) before being processed.  This decouples the engine's request
rate from the pattern generator's response latency and prevents back-pressure
on the engine's request port.

Byte Pattern
~~~~~~~~~~~~

Each 32-byte beat is filled with an incrementing byte value using a
**persistent** ``globalByteCounter`` register::

    byte[i of beat N] = (globalByteCounter + byteOffset + i) mod 256

The key property is that ``globalByteCounter`` is **never reset between work
requests** — only on hard FPGA reset.  This makes the pattern continuous
across frames::

    Work request 0 (len=3000 bytes):  0x00 0x01 0x02 ... wraps at 0xFF ...
    Work request 1 (len=3000 bytes):  continues from byte 3000 mod 256
    Work request N:                   continues from byte (N×3000) mod 256

This allows the host-side ``read_dat.py`` verification tool to check for
gaps across frame boundaries with ``--check-contiguous``.

.. note::
   If ``startAddr`` were used to seed the byte value (as in a naive
   implementation), every packet would start at ``startAddr mod 256 = 0``
   because the MR base address is page-aligned.  The persistent counter
   avoids this.

State Machine
~~~~~~~~~~~~~

.. code-block:: text

    st0_idle
      │  DmaReadReq.valid = '1'
      │  latch (initiator, sQpn, wrId, len)
      │  byteAddr ← 0  (beat offset within this request)
      ▼
    st1_send_pkg
      │  For each beat:
      │    beatBytes = min(len, 32)
      │    fill dataStream[255:0] with globalByteCounter + byteAddr + [0..31]
      │    set tKeep for beatBytes valid bytes
      │    set isFirst on first beat, isLast on last beat
      │    assert valid, wait for ready
      │
      │  On last beat:
      │    globalByteCounter += total bytes sent this request
      │    → st0_idle

Connecting in Test Firmware
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: vhdl

    U_DmaTestPatternServer : entity work.DmaTestPatternServer
        port map (
            RoceClk           => RoceClk,
            RoceRst           => RoceRst,
            dmaReadReqMaster  => roceEngineDmaReadReqMaster,
            dmaReadReqSlave   => roceEngineDmaReadReqSlave,
            dmaReadRespMaster => roceEngineDmaReadRespMaster,
            dmaReadRespSlave  => roceEngineDmaReadRespSlave
        );

No AXI-lite registers or additional configuration are required.

Verification Workflow
~~~~~~~~~~~~~~~~~~~~~

1. Start the rogue ZMQ server with ``--useRoce``.
2. Trigger work requests via ``WorkReqDispatcher.StartDispatching``.
3. The engine fetches data from ``DmaTestPatternServer`` via DMA read.
4. The engine sends RDMA WRITEs to the host MR.
5. The host CQ polling thread delivers frames to the rogue pipeline.
6. ``StreamWriter`` writes frames to a ``.dat`` file.
7. Run ``read_dat.py --check-contiguous`` to verify the byte pattern
   is continuous with no gaps across frame boundaries.
