FPGA DMA Interface
==================

The RoCEv2 engine does **not** accept an AXI-Stream directly.  Instead, it
works as an RDMA **initiator**: the user logic submits a *work request*
describing what to send, and the engine issues an internal DMA read to fetch
the payload from FPGA-side memory before packetising it into RoCEv2 frames
and sending them over the wire.

This page describes the DMA read request/response interface and the
``TestDmaServer`` module used in the test firmware to serve synthetic data.

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
data, and the DMA server (user logic or ``TestDmaServer``) responds with the
corresponding payload.

Data Flow
---------

::

    User Logic (or TestDmaServer)
         │  DmaReadResp ──────────────────────────────────────────┐
         │                                                         │
    WorkReqDispatcher                                         RoCEv2 Engine
         │  WorkReqMaster (rAddr, rKey, len, startAddr, ...)       │
         └──────────────────────────────────────────────────────► │
                                                                   │  DmaReadReq
                                                                   └──────────────►
                                                               (addr, len, qpn, wrId)
                                                                   │
                                                       User Logic / TestDmaServer
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
     - AXI-stream style valid.  Assert when a request is ready.
   * - ``initiator``
     - 4
     - Internal RoCEv2 engine initiator tag.  Echoed back in the
       response so the engine can match requests to responses when
       multiple QPs are in flight.
   * - ``sQpn``
     - 24
     - Source QP number — identifies which QP issued this request.
   * - ``wrId``
     - 64
     - Work Request ID — opaque identifier supplied in the original
       work request.  Echoed in the DMA response and in the work
       completion record.
   * - ``startAddr``
     - 64
     - Start address in FPGA-side memory of the data to fetch.
       For the ``TestDmaServer``, this address seeds the byte pattern
       (or is ignored if a persistent global counter is used).
   * - ``len``
     - 13
     - Number of bytes to return in this response (max 8192 bytes =
       one full MTU-4096 packet payload with overhead).
   * - ``mrIdx``
     - 1
     - Memory Region index selector (0 or 1), selects which of the
       FPGA's internal MRs the data belongs to.

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
     - Echoed from the request — must match the originating request's
       ``initiator`` field.
   * - ``sQpn``
     - 24
     - Source QP number — echoed from the request.
   * - ``wrId``
     - 64
     - Work Request ID — echoed from the request.
   * - ``isRespErr``
     - 1
     - Set to ``1`` to indicate a DMA read error (e.g. address out of
       range).  The engine will mark the corresponding work completion
       as failed.
   * - ``dataStream``
     - 290
     - Payload data beat (256 data bits + sideband).  The internal
       layout follows the standard SLAC AXI-Stream-256 encoding:

       .. code-block::

           dataStream[255:0]   — 32 bytes of payload data
           dataStream[263:256] — tKeep (byte enable, 8 bits)
           dataStream[264]     — tLast (last beat of this response)
           dataStream[272:265] — tDest (destination channel, 8 bits)
           dataStream[280:273] — tUser/firstUser (SSI SOF etc., 8 bits)
           dataStream[289:281] — reserved / tStrb

Response Handshake
~~~~~~~~~~~~~~~~~~

Each DMA read request generates exactly **one response transaction**,
potentially spanning multiple beats if the data is wider than 32 bytes.
The final beat has ``dataStream[264] = tLast = '1'``.

The request/response pair is matched by ``(initiator, sQpn, wrId)``.
The DMA server must echo all three fields unchanged.

.. code-block:: vhdl

    type RoceDmaReadRespSlaveType is record
        ready : sl;
    end record RoceDmaReadRespSlaveType;

----

TestDmaServer
-------------

The ``TestDmaServer`` (also referred to as ``DmaDummyServer``) is a
synthesisable VHDL module that responds to DMA read requests with a
synthetic incrementing byte pattern.  It is used in test firmware when
there is no real user data source.

Purpose
~~~~~~~

Because the RoCEv2 engine requires a DMA server on the other end of the
``RoceDmaReadReq/Resp`` interface, something must respond to DMA reads.
In the test firmware, ``TestDmaServer`` fills this role by generating
deterministic data — making it straightforward to verify correctness on
the host side.

Byte Pattern
~~~~~~~~~~~~

Each 32-byte beat is filled with an incrementing byte value::

    byte[i] = (globalByteCounter + i) mod 256

The ``globalByteCounter`` is a **persistent register** that is never reset
between work requests (only on hard reset).  This means the pattern is
**continuous across frames**::

    Work request 0 (len=3000):  00 01 02 03 ... (wraps at 0xFF) ... until 3000 bytes
    Work request 1 (len=3000):  continues from byte 3000 mod 256
    ...

This allows the host-side ``read_dat.py`` tool to verify data integrity
with a ``--check-contiguous`` flag that checks for gaps across frame
boundaries.

.. note::
   If the payload size is not a multiple of 256, the pattern still wraps
   correctly because ``globalByteCounter`` advances by the exact number
   of bytes served, not by 32-byte beat boundaries.

   Each RDMA WRITE starts its data at a fresh DMA request, but
   ``globalByteCounter`` was not reset, so the first byte of packet N is
   ``(N × len) mod 256`` — not ``0x00``.

   By contrast, if ``startAddr`` were used to seed the byte value (as in
   an earlier version), every packet would start at
   ``startAddr mod 256 = 0x00`` because the MR base address is
   page-aligned.

Design
~~~~~~

The ``TestDmaServer`` has a simple FSM:

.. code-block:: text

    st_idle
      │  DmaReadReq.valid = '1'
      │  latch (initiator, sQpn, wrId, len)
      ▼
    st_sending
      │  For each 32-byte beat:
      │    fill dataStream[255:0] with globalByteCounter + beat_offset
      │    assert valid
      │    wait for ready
      │    advance globalByteCounter by bytes_in_this_beat
      │  On last beat: set tLast = '1', return to st_idle
      ▼
    st_idle

The response rate is limited by the engine's ``ready`` signal; the server
holds ``valid`` until the beat is accepted.

Connecting in Test Firmware
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``TestDmaServer`` connects directly between the RoCEv2 engine's DMA
request/response ports:

.. code-block:: vhdl

    U_TestDmaServer : entity work.TestDmaServer
        port map (
            RoceClk             => RoceClk,
            RoceRst             => RoceRst,
            dmaReadReqMaster_i  => roceEngineDmaReadReq,   -- from engine
            dmaReadReqSlave_o   => roceEngineDmaReadReqRdy,
            dmaReadRespMaster_o => roceEngineDmaReadResp,   -- to engine
            dmaReadRespSlave_i  => roceEngineDmaReadRespRdy
        );

No AXI-lite registers are required — the ``TestDmaServer`` is fully
autonomous and requires only the clock, reset, and the DMA handshake ports.

Verification Workflow
~~~~~~~~~~~~~~~~~~~~~

1. Start the rogue ZMQ server with ``--useRoce``.
2. Run ``dispatch.py`` (or set ``startDispatching`` via pyrogue) to trigger
   work requests from the WorkReqDispatcher.
3. The engine fetches data from ``TestDmaServer`` via DMA read.
4. The engine sends RDMA WRITEs to the host MR.
5. The host CQ polling thread delivers frames to the rogue pipeline.
6. The ``StreamWriter`` writes frames to a ``.dat`` file.
7. Run ``read_dat.py --check-contiguous`` to verify the incrementing
   byte pattern with no gaps.

If the contiguity check passes, the full DMA → RoCEv2 → host MR → rogue
pipeline is confirmed working.
