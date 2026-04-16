Troubleshooting
===============

Import Errors
-------------

``ImportError: No module named rogue.protocols.rocev2``
    Rogue was not built with ``-DROCEV2=ON``, or ``libibverbs`` was not
    found at build time.  Rebuild with ``-DROCEV2=ON`` after installing
    ``rdma-core`` (see :doc:`build`).

``ImportError: libibverbs.so.1: cannot open shared object file``
    ``rdma-core`` is installed but not on ``LD_LIBRARY_PATH``.  With
    conda: ``export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH``.

RDMA Device Issues
------------------

``ibv_open_device() failed``
    * Run ``ibv_devices`` to confirm the device name (e.g. ``mlx5_0``).
    * Ensure the RDMA NIC driver is loaded: ``lsmod | grep mlx5``.
    * Check that the port is up: ``ibv_devinfo -d mlx5_0``.

``ibv_reg_mr() failed: ENOMEM``
    The MR slab is too large for the system's locked memory limit.
    Increase the locked memory limit::

        # Check current limit
        ulimit -l

        # Raise to unlimited (requires root or /etc/security/limits.conf)
        ulimit -l unlimited

    Or add to ``/etc/security/limits.conf``::

        * soft memlock unlimited
        * hard memlock unlimited

``ibv_modify_qp() failed on RTR transition``
    * The FPGA GID is incorrect.  Verify the FPGA IP address and that
      the GID derivation (``::ffff:<fpga_ip>``) matches the FPGA's actual
      GID.
    * The FPGA QP number may not be valid.  Check that the QP create
      metadata transaction succeeded (``successOrNot = 1``).
    * The path MTU may be larger than the link supports.  Try
      ``IBV_MTU_1024`` or ``IBV_MTU_2048`` if ``IBV_MTU_4096`` fails.

Metadata Bus Issues
-------------------

``TimeoutError: Timed out waiting for MetaDataRx response``
    * The FPGA firmware is not responding.  Check that the SRP/UDP
      register path is working: try reading a known register
      (e.g. ``AxiVersion.FpgaVersion``).
    * The ``SendMetaData`` pulse may not have triggered a rising edge.
      Ensure ``0`` is written before ``1``.
    * The FPGA QP state machine may be stuck.  Reset the FPGA and
      re-run the handshake.

``RoceMetaDataError: FPGA returned failure for PD alloc``
    The FPGA's PD resource pool is exhausted (``MAX_PD = 1`` — only one PD
    is supported).  The previous session's PD was not freed, most likely
    because the ZMQ server was killed without a clean shutdown.  Reset the
    FPGA firmware before restarting.

``RecvMetaData stays 0 after first transaction``
    The FPGA state machine may have stalled.  This can happen if
    ``SendMetaData`` was never de-asserted.  Always write ``0→1→0``:

    .. code-block:: python

        engine.SendMetaData.set(0)
        engine.MetaDataTx.set(tx_val)
        engine.SendMetaData.set(1)
        engine.SendMetaData.set(0)   # ← do not forget this

Data Path Issues
----------------

``RxFrameCount not incrementing``
    * The FPGA QP may not have reached RTS.  Check
      ``root.Rdma.ConnectionState.get()`` — it should read ``'Connected'``.
    * The WorkReqDispatcher ``RAddr``/``RKey`` may not match the host MR.
      Verify ``root.Rdma.MrAddr.get()`` equals the value written to
      ``engine.RAddr``.
    * The FPGA data source may not be sending.  Check FPGA-side status
      registers.

``CQ poll returns IBV_WC_REM_ACCESS_ERR``
    The FPGA is using an incorrect ``rkey`` or writing outside the MR
    bounds.  Verify that ``rkeyPart`` in the MR allocation message
    matches ``host_mr.rkey >> MR_INDEX_B``.

``Frames have wrong size or appear truncated``
    The ``FrameLen`` written to the WorkReqDispatcher must match
    ``maxPayload`` used when registering the MR.

SoftRoCE Issues
---------------

``rdma link add rxe0 type rxe netdev eth0`` fails with "Operation not supported"
    The ``rdma_rxe`` kernel module is not loaded.  Run
    ``sudo modprobe rdma_rxe`` and retry.

``rdma link show`` shows ``rxe0`` but ``ibv_devices`` is empty
    The ``rdma-core`` userspace library is not seeing the kernel device.
    Try ``sudo rdma link show`` — permissions may be required.  Also ensure
    the ``rdma-core`` package is installed (not just ``libibverbs``).

``ibv_devinfo`` reports port state ``DOWN`` on ``rxe0``
    The underlying Ethernet interface is down or has no IP address.
    Bring it up: ``sudo ip link set eth0 up`` and assign an IP if needed.

SoftRoCE connection established but no frames received
    SoftRoCE uses the Linux network stack, so ensure there is no firewall
    rule blocking UDP port 4791 (the mandatory RoCEv2 port)::

        sudo iptables -I INPUT -p udp --dport 4791 -j ACCEPT
        sudo iptables -I OUTPUT -p udp --sport 4791 -j ACCEPT

    Also verify the FPGA can reach the host IP on the interface attached
    to ``rxe0``.

``rxe0`` disappears after reboot
    The ``rdma link add`` command is not persistent.  To restore it on
    boot, create a systemd service or add to a network startup script::

        # /etc/networkd-dispatcher/routable.d/50-rxe0
        #!/bin/bash
        [ "$IFACE" = "eth0" ] && rdma link add rxe0 type rxe netdev eth0

Performance Issues
------------------

``Throughput lower than expected``
    * Check DCQCN is not throttling aggressively: read
      ``DcqcnRateIncInt`` and compare to defaults.  If ECN is not
      configured on the switch, DCQCN will oscillate unnecessarily.
    * Ensure the NIC is in RoCEv2 mode (not IB mode):
      ``mlnx_tune -t HIGH_THROUGHPUT`` (with MLNX_OFED).
    * Check ``RxErrorCount`` for CQ errors that cause retransmissions.

``High CPU usage on receive``
    The CQ polling thread uses busy-polling by default.  Set
    ``pollIntervalMs > 0`` on ``RoCEv2Server`` to trade latency for
    CPU cycles (e.g. ``pollIntervalMs=1`` for 1 ms sleep between polls).
