RoCEv2Server
============

``pyrogue.protocols.RoCEv2Server`` is a :class:`pyrogue.Device` subclass that
owns the C++ ``Server`` object, contains all metadata bus logic internally,
and orchestrates the full connection handshake on ``_start()`` and teardown
on ``_stop()``.

There is no separate ``RoceEngine`` device — the metadata bus encoding,
decoding, and AXI-lite register access are all integrated directly into
``RoCEv2Server``.

Constructor Parameters
----------------------

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter
     - Type
     - Description
   * - ``name``
     - str
     - pyrogue device name
   * - ``ip``
     - str
     - FPGA IP address.  Used to derive the FPGA GID as ``::ffff:<ip>``.
   * - ``rdmaDevice``
     - str
     - RDMA device name (e.g. ``'mlx5_0'``, ``'rxe0'``).
       Use ``ibv_devices`` to list available devices.
   * - ``rxQueueDepth``
     - int
     - Number of receive slots in the MR slab.
       Defaults to ``rogue.protocols.rocev2.DefaultRxQueueDepth``.
   * - ``maxPayload``
     - int
     - Maximum payload bytes per frame / MR slot.
       Defaults to ``rogue.protocols.rocev2.DefaultMaxPayload``.
   * - ``pollInterval``
     - int
     - Poll interval in seconds for ``RxFrameCount`` / ``RxByteCount``
       status variables (default 1).
   * - ``**kwargs``
     - Any
     - Forwarded to :class:`pyrogue.Device`.

pyrogue Variables
-----------------

All variables are read-only (``mode='RO'``).  They are populated after
``_start()`` completes.

.. list-table::
   :header-rows: 1
   :widths: 25 12 63

   * - Name
     - Type
     - Description
   * - ``FpgaIp``
     - str
     - FPGA IP address supplied at construction.  Used for GID derivation.
   * - ``FpgaGid``
     - str
     - FPGA GID in colon-separated hex notation (``::ffff:<ip>``).
   * - ``HostQpn``
     - UInt32
     - Host RC QP number.
   * - ``HostGid``
     - str
     - Host GID (NIC RoCEv2 address).
   * - ``HostRqPsn``
     - UInt32
     - Host starting receive PSN.  The FPGA SQ PSN must match this.
   * - ``HostSqPsn``
     - UInt32
     - Host starting send PSN.  The FPGA RQ PSN must match this.
   * - ``MrAddr``
     - UInt64
     - Virtual address of the registered MR slab.
       Written to the FPGA WorkReqDispatcher ``RAddr`` register.
   * - ``MrRkey``
     - UInt32
     - Remote key of the MR.  Written to FPGA WorkReqDispatcher ``RKey``.
   * - ``FpgaQpn``
     - UInt32
     - FPGA QP number returned by the QP create metadata response.
       Set to 0 before ``_start()`` completes.
   * - ``FpgaLkey``
     - UInt32
     - FPGA MR local key returned by the MR allocation metadata response.
       Written to the WorkReqDispatcher ``lKey`` register.
   * - ``MaxPayload``
     - UInt32
     - Max payload bytes per RDMA WRITE slot (construction parameter).
   * - ``RxQueueDepth``
     - UInt32
     - Number of receive slots (construction parameter).
   * - ``ConnectionState``
     - str
     - Current lifecycle state.  See :doc:`../integration/connection_lifecycle`
       for all possible values.
   * - ``RxFrameCount``
     - UInt64
     - Total frames received since startup.  Polled every ``pollInterval`` s.
   * - ``RxByteCount``
     - UInt64
     - Total bytes received since startup.  Polled every ``pollInterval`` s.

Methods
-------

``application(channelId: int) → rogue.interfaces.stream.Master``
    Returns the stream master for the given channel ID (0–255).
    Downstream consumers connect to this port.

``_start() → None``
    Called automatically by the pyrogue startup sequence.  Performs:

    1. C++ ``Server`` construction (MR registration, QP creation to INIT).
    2. Full metadata bus handshake: PD alloc → MR alloc → QP create →
       INIT → RTR → RTS (both sides).
    3. WorkReqDispatcher register writes (``RAddr``, ``RKey``, etc.).
    4. DCQCN initial configuration.
    5. Starts the CQ polling thread.
    6. Sets ``ConnectionState = 'Connected'``.

``_stop() → None``
    Called automatically by the pyrogue shutdown sequence.  Performs:

    1. Stops the CQ polling thread.
    2. Tears down the FPGA QP/MR/PD via the metadata bus.
    3. Destroys host libibverbs resources (QP, MR, CQ, PD).
    4. Sets ``ConnectionState = 'Disconnected'``.
