Quick Start
===========

Prerequisites
-------------

* A host with an RDMA-capable NIC (RoCEv2 mode, e.g. Mellanox/NVIDIA ConnectX).
* ``rdma-core`` / ``libibverbs`` installed (available via conda-forge as
  ``rdma-core``).
* Rogue built with ``-DROCEV2=ON`` (see :doc:`../appendix/build`).
* An FPGA loaded with firmware that includes the BSV RoCEv2 engine and the
  SRP/UDP register path.

Minimal Example
---------------

The following snippet mirrors the pattern of the existing
:class:`pyrogue.protocols.UdpRssiPack` — drop-in replacement for the
stream data path:

.. code-block:: python

    import pyrogue as pr
    import pyrogue.protocols

    class MyRoot(pr.Root):
        def __init__(self, fpgaIp, **kwargs):
            super().__init__(**kwargs)

            # ── SRP / register access (unchanged) ──────────────────────
            udp  = rogue.protocols.udp.Client(fpgaIp, 8192, False)
            srp  = rogue.protocols.srp.SrpV3()
            udp  == srp

            # ── RoCEv2 data stream (replaces UdpRssiPack) ───────────────
            self.rdma = pyrogue.protocols.RoCEv2Server(
                name         = 'RdmaRx',
                fpgaIp       = fpgaIp,
                rdmaDevice   = 'mlx5_0',    # ibv_devices to list
                rxQueueDepth = 256,
                maxPayload   = 8192,
            )
            self.add(self.rdma)

            # Add the RoCEv2 engine register device under the same
            # memory map as other FPGA peripherals
            self.add(pyrogue.protocols.RoceEngine(
                name   = 'RoceEngine',
                memBase= srp,
                offset = 0x0000_A000,       # base address of the engine
            ))

            # Wire the engine to the server so _start() can handshake
            self.rdma.setEngine(self.RoceEngine)

            # ── Application device ──────────────────────────────────────
            self.add(MyDevice(
                name    = 'Detector',
                memBase = srp,
                offset  = 0x0000_0000,
            ))
            # Connect channel 0 of the RDMA stream to the device
            self.rdma.application(0) >> self.Detector.dataStream

    with MyRoot(fpgaIp='192.168.1.10') as root:
        pr.streamTap(root.rdma.application(0), pr.utilities.fileio.StreamWriter())
        root.start()
        # … run …

.. note::
   ``RoCEv2Server.application(channelId)`` returns a stream master/slave
   interface identical to ``packetizer.Core.application(dest)``.  Existing
   code that connects the packetizer output needs no change — just swap the
   object.

Checking the Connection
-----------------------

After ``root.start()`` the Python layer has completed the FPGA handshake.
You can verify the RDMA link with:

.. code-block:: python

    print(root.RdmaRx.QpState.get())    # should be 'RTS'
    print(root.RdmaRx.MrAddr.get())     # host MR virtual address
    print(root.RdmaRx.MrRkey.get())     # host MR rkey (sent to FPGA)
    print(root.RdmaRx.RxFrameCount.get())  # increments with each RDMA WRITE
