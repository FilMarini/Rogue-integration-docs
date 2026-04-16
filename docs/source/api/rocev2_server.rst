RoCEv2Server (Python)
=====================

``pyrogue.protocols.RoCEv2Server`` is a :class:`pyrogue.Device` subclass that
owns the C++ ``Server`` object and orchestrates the connection handshake.

Class Reference
---------------

.. code-block:: python

    class pyrogue.protocols.RoCEv2Server(pr.Device):

Constructor Parameters
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter
     - Type
     - Description
   * - ``name``
     - str
     - pyrogue device name
   * - ``fpgaIp``
     - str
     - FPGA IP address (used to derive FPGA GID as ``::ffff:<ip>``)
   * - ``rdmaDevice``
     - str
     - RDMA device name (e.g. ``'mlx5_0'``). Use ``ibv_devices`` to
       list available devices.
   * - ``rxQueueDepth``
     - int
     - Number of receive slots in the MR slab.
       Defaults to ``rogue.protocols.rocev2.DefaultRxQueueDepth``.
   * - ``maxPayload``
     - int
     - Maximum payload bytes per frame.
       Defaults to ``rogue.protocols.rocev2.DefaultMaxPayload``.
   * - ``pollIntervalMs``
     - int
     - CQ polling interval in milliseconds (default 0 = busy poll).
   * - ``**kwargs``
     - Any
     - Forwarded to :class:`pyrogue.Device`.

pyrogue Variables
~~~~~~~~~~~~~~~~~

The following variables are accessible from the pyrogue tree after
``root.start()``:

.. list-table::
   :header-rows: 1
   :widths: 25 10 15 50

   * - Name
     - Mode
     - Type
     - Description
   * - ``MrAddr``
     - RO
     - UInt64
     - Virtual address of the registered MR slab.
   * - ``MrRkey``
     - RO
     - UInt32
     - Remote key of the MR (sent to FPGA during handshake).
   * - ``MrLength``
     - RO
     - UInt64
     - Length of the MR slab in bytes (= ``rxQueueDepth × maxPayload``).
   * - ``HostQpNum``
     - RO
     - UInt32
     - Host QP number (sent to FPGA during RTR transition).
   * - ``HostGid``
     - RO
     - str
     - Host GID in colon-separated hex notation.
   * - ``FpgaQpNum``
     - RO
     - UInt32
     - FPGA QP number (returned by QP create response).
   * - ``FpgaLkey``
     - RO
     - UInt32
     - FPGA local key returned by the MR allocation response.
       Written to the WorkReqDispatcher ``lKey`` register.
   * - ``QpState``
     - RO
     - str
     - Current QP state string (``'RTS'``, ``'RTR'``, etc.).
   * - ``RxFrameCount``
     - RO
     - UInt64
     - Total frames received since startup. Polled every second.
   * - ``RxByteCount``
     - RO
     - UInt64
     - Total bytes received since startup.
   * - ``RxErrorCount``
     - RO
     - UInt32
     - CQ error completions since startup.

Methods
~~~~~~~

``application(channelId: int) → rogue.interfaces.stream.Master``
    Returns the stream master for the given channel ID (0–255).
    Downstream consumers connect to this, identical to
    ``packetizer.Core.application(dest)``.

``setEngine(engine: pyrogue.protocols.RoceEngine) → None``
    Associate a :class:`RoceEngine` device instance.  Must be called
    before ``root.start()``.

``_start() → None``
    Called automatically by the pyrogue startup sequence.  Performs:

    1. C++ ``Server`` construction (MR registration, QP creation).
    2. ``engine._setup_connection(server)`` — full metadata bus handshake.
    3. WorkReqDispatcher register writes.
    4. DCQCN initial configuration.
    5. Starts the CQ polling thread.

``_stop() → None``
    Stops the CQ polling thread and destroys libibverbs resources.

Usage Example
~~~~~~~~~~~~~

.. code-block:: python

    import pyrogue as pr
    import pyrogue.protocols

    class MyRoot(pr.Root):
        def __init__(self, fpgaIp, **kwargs):
            super().__init__(**kwargs)

            # Standard SRP/UDP register path
            udp = rogue.protocols.udp.Client(fpgaIp, 8192, False)
            srp = rogue.protocols.srp.SrpV3()
            udp == srp

            # RoCEv2 receive
            self.add(pyrogue.protocols.RoCEv2Server(
                name         = 'Rdma',
                fpgaIp       = fpgaIp,
                rdmaDevice   = 'mlx5_0',
                rxQueueDepth = 512,
                maxPayload   = 8192,
            ))

            # FPGA RoCEv2 engine register map
            self.add(pyrogue.protocols.RoceEngine(
                name   = 'RoceEngine',
                memBase= srp,
                offset = 0x0000_A000,
            ))

            # Wire them together
            self.Rdma.setEngine(self.RoceEngine)

            # Application stream
            pr.streamConnect(self.Rdma.application(0), myConsumer)
