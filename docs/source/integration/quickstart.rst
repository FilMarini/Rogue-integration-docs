Quick Start
===========

Prerequisites
-------------

* A host with an RDMA-capable NIC in RoCEv2 mode (e.g. Mellanox/NVIDIA
  ConnectX), or a softRoCE interface (``rxe0``).
* ``rdma-core`` / ``libibverbs`` installed (available via conda-forge as
  ``rdma-core``).
* Rogue built from source with ``libibverbs`` available at build time
  (see :doc:`../appendix/build`).
* An FPGA loaded with firmware that includes the SLAC RoCEv2 engine and the
  SRP/UDP register path.

Example Design
--------------

A complete working example — including the pyrogue root, ``RoCEv2Server``
instantiation, SRP/UDP wiring, and ZMQ server startup — can be found in the
``Simple-10GbE-RUDP-KCU105-Example`` repository on GitHub:

    https://github.com/slaclab/Simple-10GbE-RUDP-KCU105-Example

Refer to that repository's ``startZmq.py`` and associated root class for a
concrete integration pattern.

Checking the Connection
-----------------------

After ``root.start()`` the Python layer has completed the FPGA handshake.
You can verify the RDMA link from a ZMQ client with:

.. code-block:: python

    import pyrogue.interfaces

    with pyrogue.interfaces.VirtualClient(addr='localhost', port=9099) as c:
        rx = c.root.rdmaRx   # adjust path to match your root

        print('ConnectionState :', rx.ConnectionState.get())  # 'Connected'
        print('FpgaIp          :', rx.FpgaIp.get())
        print('FpgaGid         :', rx.FpgaGid.get())
        print('HostQpn         :', hex(rx.HostQpn.get()))
        print('HostGid         :', rx.HostGid.get())
        print('HostRqPsn       :', hex(rx.HostRqPsn.get()))
        print('HostSqPsn       :', hex(rx.HostSqPsn.get()))
        print('MrAddr          :', hex(rx.MrAddr.get()))
        print('MrRkey          :', hex(rx.MrRkey.get()))
        print('FpgaQpn         :', hex(rx.FpgaQpn.get()))
        print('FpgaLkey        :', hex(rx.FpgaLkey.get()))
        print('MaxPayload      :', rx.MaxPayload.get())
        print('RxQueueDepth    :', rx.RxQueueDepth.get())
        print('RxFrameCount    :', rx.RxFrameCount.get())
        print('RxByteCount     :', rx.RxByteCount.get())
