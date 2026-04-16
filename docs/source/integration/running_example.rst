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

Open the target's top-level entity and ensure the generic is set to ``true``:

.. code-block:: vhdl

    ROCEV2_EN_G => true

Then build the bitfile using ruckus:

.. code-block:: bash

    make bit

.. note::
   If ``ROCEV2_EN_G`` is ``false``, the RoCEv2 engine is excluded from the
   design and the firmware behaves exactly like the original example design,
   using plain UDP/RSSI for data transport.

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

Verify the RDMA link is active before proceeding:

.. code-block:: bash

    rdma link
    # Expected:
    # link rxe0/1 state ACTIVE physical_state LINK_UP netdev <interface>

The ``state ACTIVE`` line confirms the RDMA link is ready.  The name to pass
as ``--roceDevice`` is the RDMA device name shown on the left of this output
— in the example above that is ``rxe0``.

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
       (``IBV_MTU_4096``), recommended for 10 GbE.
   * - ``--roceOffset``
     - AXI-lite byte offset of the RoCEv2 engine register block within
       the FPGA address map.  Must match the firmware.
       For the KCU105 example: ``0x00150000``.
   * - ``--roceMinRnrTimer``
     - Minimum RNR NAK timer value set on the host QP.  Controls the
       minimum time the host signals it needs before the FPGA may retry
       after an RNR NAK.  ``31`` ≈ 491 ms (maximum, recommended for
       SoftRoCE).
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
     - Enable DCQCN congestion control.  Writes the initial DCQCN register
       values to the FPGA engine during startup (see :doc:`../dcqcn/registers`).
       Recommended whenever the link may experience congestion.

Expected output
~~~~~~~~~~~~~~~

If the RDMA connection is established successfully the server prints the
full connection summary.  A typical successful run looks like::

    Rogue/pyrogue version v6.10.1  https://github.com/slaclab/rogue
    INFO:pyrogue.Root.Root.Root:Making device Root
    INFO:...rdmaRx:RoCEv2 'rdmaRx': QPN=0x000017  GID=...  MR=0x62931ea90000  rkey=0x0000087c  FPGA GID=...
    INFO:...rdmaRx:RoceEngine: PD allocated handler=0x06a56240
    INFO:...rdmaRx:RoceEngine: MR allocated lkey=0x19a02fe6 rkey=0x3988d946
    INFO:...rdmaRx:RoceEngine: QP created fpga_qpn=0xa56240
    INFO:...rdmaRx:RoceEngine: QP → INIT
    INFO:...rdmaRx:RoceEngine: QP → RTR targeting host qpn=0x000017
    INFO:...rdmaRx:RoceEngine: QP → RTS — FPGA ready to send RDMA WRITEs
    INFO:...rdmaRx:============================================================
    INFO:...rdmaRx:RoCEv2 FPGA connection summary
    INFO:...rdmaRx:  FPGA QPN    : 0xa56240
    INFO:...rdmaRx:  FPGA lkey   : 0x19a02fe6
    INFO:...rdmaRx:  FPGA state  : RTS (ready to send RDMA WRITEs)
    INFO:...rdmaRx:  Host QPN    : 0x000017
    INFO:...rdmaRx:  Host RQ PSN : 0x8b4567
    INFO:...rdmaRx:  Host SQ PSN : 0x7b23c6
    INFO:...rdmaRx:  MR addr     : 0x000062931ea90000
    INFO:...rdmaRx:  MR length   : 262144 bytes
    INFO:...rdmaRx:  Path MTU    : 5 (4096 bytes)
    INFO:...rdmaRx:============================================================
    INFO:...rdmaRx:RoCEv2 host RC connection summary
    INFO:...rdmaRx:  Device      : rxe0  port=1  GID idx=1
    INFO:...rdmaRx:  Host QPN    : 0x000017
    INFO:...rdmaRx:  Host GID    : 0000:0000:0000:0000:0000:ffff:c0a8:0264
    INFO:...rdmaRx:  Host state  : RTS
    INFO:...rdmaRx:  MR addr     : 0x000062931ea90000
    INFO:...rdmaRx:  MR rkey     : 0x0000087c
    INFO:...rdmaRx:  MR size     : 262144 bytes  (256 slots x 1024 bytes)
    INFO:...rdmaRx:  FPGA QPN    : 0xa56240
    INFO:...rdmaRx:  FPGA lkey   : 0x19a02fe6
    INFO:...rdmaRx:  FPGA GID    : 0000:0000:0000:0000:0000:ffff:c0a8:020a
    INFO:...rdmaRx:  Path MTU    : 5 (4096 bytes)
    INFO:...rdmaRx:  MinRnrTimer : 31
    INFO:...rdmaRx:  RnrRetry    : 7
    INFO:...rdmaRx:  RetryCount  : 3
    INFO:...rdmaRx:  RC connection established — ready to receive RDMA WRITEs
    INFO:...rdmaRx:============================================================
    INFO:pyrogue.Root.Root.Root:Root lifecycle started
    Running. Hit cntrl-c or send SIGTERM to <pid> to exit.

The two summary blocks confirm both sides of the connection.  The key line
to look for is::

    RC connection established — ready to receive RDMA WRITEs

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

In the GUI, navigate to **DataWriter** and:

1. Set the **DataFile** field to your desired output path, e.g.
   ``/tmp/test_roce.dat``.
2. Click **Open**.

Step 6 — Dispatch Work Requests
---------------------------------

Trigger the WorkReqDispatcher to send frames from the FPGA to the host.
From the ``software/scripts/`` directory:

.. code-block:: bash

    python3 runDispatch.py --cases 100

This sends 100 RDMA WRITEs from the FPGA.  While dispatching, watch the
GUI — ``rdmaRx.RxFrameCount`` should increment with each received frame.
The ``WorkCompChecker.SuccessCounter`` register on the FPGA side should
match the number of dispatched cases.

Step 7 — Close the Stream Writer File
---------------------------------------

Once ``RxFrameCount`` in the GUI matches the number of dispatched cases,
navigate back to **DataWriter** and click **Close**.

Step 8 — Verify the Data
--------------------------

Check that the written data is correct and contiguous using the
``fileReader.py`` utility:

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
``DmaTestPatternServer`` is continuous across frame boundaries — no gaps
and no resets to ``0x00`` between frames.  Any gap indicates a missed or
out-of-order RDMA WRITE.

Troubleshooting the Example
----------------------------

**Server exits with "FPGA PD allocation failed"**
    The FPGA firmware was not reset between runs and the previous session's
    PD was not freed (``MAX_PD = 1``).  Power-cycle the KCU105 or reload
    the bitfile, then relaunch.  See :doc:`connection_lifecycle` for details.

**``rdma link`` shows ``state ACTIVE`` but ping to 192.168.2.10 fails**
    The host interface IP is not in the same subnet.  Verify with
    ``ip addr show <interface>`` and reassign if needed.

**Frames are received but ``fileReader.py`` reports gaps**
    Some RDMA WRITEs arrived while the host MR slots were not yet drained.
    Increase ``--roceMinRnrTimer`` to ``31`` (491 ms) and check
    ``WorkCompChecker.UnsuccessCounter`` for non-zero values.

**``RxFrameCount`` is lower than ``--cases``**
    Check ``WorkCompChecker.UnsuccessCounter`` and ``rdmaRx.RxByteCount``
    to distinguish between RDMA-level failures and host-side drops.
