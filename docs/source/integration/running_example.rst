Running the Example Design
==========================

This page walks through a complete end-to-end test using the
``Simple-10GbE-RUDP-KCU105-Example`` firmware and software.

Prerequisites
-------------

* KCU105 evaluation board programmed with a bitfile built with
  ``ROCEV2_EN_G => true`` (see :ref:`firmware-build` below).
* Host machine connected to the KCU105 via a 10 GbE link (SFP or copper).
* Rogue built with ``-DROCEV2=ON`` (see :doc:`../appendix/build`).
* A working RDMA interface on the host — either a hardware RoCEv2 NIC
  or a SoftRoCE link (see :doc:`../appendix/build` §Setting Up SoftRoCE).

.. _firmware-build:

Step 1 — Build the Firmware with RoCEv2 Enabled
------------------------------------------------

Open the target's top-level VHDL or tcl build file and ensure the generic
is set:

.. code-block:: vhdl

    ROCEV2_EN_G => true

Then build the bitfile using Vivado as usual (``make`` or ``source build.tcl``
depending on the project).  Without ``ROCEV2_EN_G => true`` the RoCEv2 engine
is excluded from the design and the firmware will behave as a plain UDP device.

Step 2 — Set Up the Network Link
---------------------------------

Connect the KCU105 SFP/copper port to the host NIC.  The default FPGA IP
address is ``192.168.2.10``.  Configure the host interface to be on the same
subnet:

.. code-block:: bash

    sudo ip addr add 192.168.2.1/24 dev <interface>
    sudo ip link set <interface> up

    # Verify connectivity
    ping 192.168.2.10

If using SoftRoCE, attach it to the same interface (replace ``<interface>``
with the actual name, e.g. ``enp34s0``):

.. code-block:: bash

    sudo modprobe rdma_rxe
    sudo rdma link add rxe0 type rxe netdev <interface>

Verify the link is active before proceeding:

.. code-block:: bash

    rdma link
    # Expected:
    # link rxe0/1 state ACTIVE physical_state LINK_UP netdev <interface>

The ``state ACTIVE`` line confirms the RDMA link is ready.  The ``--roceDevice``
argument passed to ``startZmq.py`` is the RDMA device name shown by
``rdma link`` — in the example above that is ``rxe0``.

Step 3 — Launch the ZMQ Server
--------------------------------

From the ``software/scripts/`` directory of the example project:

.. code-block:: bash

    python3 startZmq.py \
        --ip              192.168.2.10 \
        --useRoce \
        --roceDevice      rxe0 \
        --rocePmtu        5 \
        --roceOffset      0x00150000 \
        --roceMinRnrTimer 31 \
        --roceRnrRetry    7 \
        --roceRetryCount  3 \
        --roceMaxPay      1024 \
        --useDcqcn

Argument reference:

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Argument
     - Description
   * - ``--ip``
     - FPGA IP address.  Default: ``192.168.2.10``.
   * - ``--useRoce``
     - Enable the RoCEv2 receive path instead of UDP/RSSI.
   * - ``--roceDevice``
     - RDMA device name as shown by ``rdma link`` (e.g. ``rxe0`` for
       SoftRoCE, ``mlx5_0`` for a hardware NIC).
   * - ``--rocePmtu``
     - Path MTU code passed to the FPGA QP.  ``5`` = 4096 bytes
       (``IBV_MTU_4096``), which is recommended for 10 GbE.
   * - ``--roceOffset``
     - AXI-lite byte offset of the RoCEv2 engine register block within
       the FPGA address map.  Must match the firmware.
       For the KCU105 example: ``0x00150000``.
   * - ``--roceMinRnrTimer``
     - Minimum RNR NAK timer value set on the host QP.  Controls the
       minimum time the host signals it needs before the FPGA may retry
       after an RNR.  ``31`` ≈ 491 ms (maximum, recommended for SoftRoCE).
   * - ``--roceRnrRetry``
     - Number of times the FPGA retries after receiving an RNR NAK.
       ``7`` = infinite retries.
   * - ``--roceRetryCount``
     - Number of times the FPGA retries after a non-RNR error (timeout,
       sequence error).  Default: ``3``.
   * - ``--roceMaxPay``
     - Maximum payload size in bytes per RDMA WRITE slot.  Must be ≤ the
       path MTU.  Example: ``1024``.
   * - ``--useDcqcn``
     - Enable DCQCN congestion control registers on startup.

Once the server is running you should see output similar to::

    Rogue/pyrogue version v6.x.x  https://github.com/slaclab/rogue
    Start: Started zmqServer on ports 9099-9101
        To start a gui: python -m pyrogue gui --server='localhost:9099'
        To use a virtual client: client = pyrogue.interfaces.VirtualClient(...)

A successful RDMA connection will produce log lines showing the metadata
bus handshake completing and ``ConnectionState`` transitioning to
``'Connected'``.

Step 4 — Launch the GUI
-----------------------

In a separate terminal, open the pyrogue GUI:

.. code-block:: bash

    python -m pyrogue gui --server='localhost:9099'

The GUI tree will show the full device hierarchy.  Navigate to the
``rdmaRx`` device to inspect connection parameters (``MrAddr``, ``MrRkey``,
``FpgaQpn``, etc.) and frame counters (``RxFrameCount``, ``RxByteCount``).

Step 5 — Open a Stream Writer File
------------------------------------

In the GUI, navigate to **DataWriter** (or **StreamWriter**) and:

1. Set the **DataFile** field to your desired output path, e.g.
   ``/tmp/test_roce.dat``.
2. Click **Open** (or set ``Open = True``).

The file writer is now recording all incoming RDMA frames to disk.

Alternatively, from a ZMQ client script:

.. code-block:: python

    import pyrogue.interfaces

    with pyrogue.interfaces.VirtualClient(addr='localhost', port=9099) as c:
        c.root.DataWriter.DataFile.set('/tmp/test_roce.dat')
        c.root.DataWriter.Open.set(True)

Step 6 — Dispatch Work Requests
---------------------------------

Trigger the WorkReqDispatcher to send frames from the FPGA to the host.
From the ``software/scripts/`` directory:

.. code-block:: bash

    python3 runDispatch.py --cases 100

This sends 100 RDMA WRITEs from the FPGA.  The ``--cases`` argument sets
the number of work requests dispatched.

While dispatching, watch the GUI — ``rdmaRx.RxFrameCount`` should increment
with each received frame.  The ``WorkCompChecker.SuccessCounter`` register on
the FPGA side should match the number of dispatched cases.

Step 7 — Close the Stream Writer File
---------------------------------------

Once ``RxFrameCount`` matches the number of dispatched cases, close the file:

In the GUI, click **Close** on the DataWriter, or from a script:

.. code-block:: python

    with pyrogue.interfaces.VirtualClient(addr='localhost', port=9099) as c:
        c.root.DataWriter.Open.set(False)
        print('File size:', c.root.DataWriter.FileSize.get(), 'bytes')
        print('Frames written:', c.root.DataWriter.FrameCount.get())

Step 8 — Verify the Data
--------------------------

Check that the written data is correct and contiguous using the
``fileReader.py`` utility from the ``software/scripts/`` directory:

.. code-block:: bash

    python3 fileReader.py \
        --dataFile /tmp/test_roce.dat \
        --check-cont

Expected output on success::

    Frame      1 | size=  1024 bytes | channel=0
    Frame      2 | size=  1024 bytes | channel=0
    ...
    Frame    100 | size=  1024 bytes | channel=0

    Total: 100 frame(s), 102400 bytes (100.0 KB)
    Contiguity: OK — no gaps detected

The ``--check-cont`` flag verifies that the byte pattern written by
``DmaTestPatternServer`` is continuous across frame boundaries (no gaps,
no resets to 0x00 between frames).  Any gap indicates a missed or
out-of-order RDMA WRITE.

Troubleshooting the Example
----------------------------

**Server exits immediately with "FPGA PD allocation failed"**
    The FPGA firmware was not reset between runs and the previous session's
    PD was not freed.  Power-cycle the KCU105 or reload the bitfile, then
    relaunch the server.  See :doc:`connection_lifecycle` for why
    ``MAX_PD = 1`` makes this necessary.

**``rdma link`` shows ``state ACTIVE`` but ping to 192.168.2.10 fails**
    The host interface IP is not in the same subnet as the FPGA.  Verify
    with ``ip addr show <interface>`` and reassign if needed.

**Frames are received but ``fileReader.py`` reports gaps**
    Increase ``--roceMinRnrTimer`` to give the host more time to drain
    the MR slots between writes.  With SoftRoCE under load, ``31``
    (491 ms) is recommended.  Also check ``WorkCompChecker.UnsuccessCounter``
    — non-zero means some WRITEs failed at the RDMA level.

**``RxFrameCount`` is lower than ``--cases``**
    Some WRITEs were dropped.  Check ``WorkCompChecker.UnsuccessCounter``
    and ``rdmaRx.RxByteCount`` to distinguish between RDMA-level failures
    and host-side drops.
