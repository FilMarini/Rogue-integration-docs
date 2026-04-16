Connection Flow
===============

This page describes the complete startup sequence that establishes the RDMA
connection between the host and the FPGA.  The sequence is executed
automatically by ``RoCEv2Server._start()``.

.. seealso::
   For the full connection lifecycle across ZMQ server restarts and crash
   recovery, including teardown probe logic and the ``ConnectionState``
   variable, see :doc:`connection_lifecycle`.

Sequence Diagram
-----------------

::

    HOST (Python / C++)                  FPGA (RoCEv2 Engine)
    ─────────────────────────────────    ───────────────────────────────

    1. ibv_reg_mr()
       → mr.addr, mr.rkey

    2. ibv_create_qp() + RESET→INIT
       → host_qp_num, host_gid

    3. MetaData TX: PD alloc ──────────► PD alloc request
       ◄──────────────────────────────── PD alloc response: pdHandler

    4. MetaData TX: MR alloc ──────────► MR alloc request
       (carry: addr, rkey, len,            (FPGA stores addr+rkey
        accFlags, pdHandler)               internally for WRITE ops)
       ◄──────────────────────────────── MR alloc response: lkey

    5. MetaData TX: QP create ─────────► QP create request
       (carry: pdHandler, type=RC)
       ◄──────────────────────────────── QP create response: fpga_qp_num

    6. MetaData TX: QP INIT ───────────► QP INIT request

    7. MetaData TX: QP RTR ────────────► QP RTR request
       (carry: host_qp_num, host_gid,      (FPGA transitions QP to RTR)
        host_psn, path_mtu)
       ◄──────────────────────────────── QP RTR response: success

    8. host: INIT → RTR
       (using fpga_qp_num, fpga_gid)

    9. MetaData TX: QP RTS ────────────► QP RTS request
       (carry: retry_cnt, rnr_retry,        (FPGA transitions QP to RTS)
        timeout, sq_psn)
       ◄──────────────────────────────── QP RTS response: success

    10. host: RTR → RTS

    11. Write WorkReqDispatcher regs:
        RAddr = mr.addr
        RKey  = mr.rkey
        AddrWrapCount = rxQueueDepth
        FrameLen = maxPayload

    ══════════ Connection established ═════════════════════════════════

    12. FPGA starts RDMA WRITE-with-Imm ─────────────────────────────►
                                          (to mr.addr, using mr.rkey)

    13. Host CQ polling thread receives IBV_WC_RECV_RDMA_WITH_IMM
        → extract channel_id from imm_data[31:24]
        → build rogue Frame
        → sendFrame(channel_id, frame)

Detailed Steps
--------------

Step 1–2: Host RDMA Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~

Performed in the C++ ``Server`` constructor (see :doc:`host_side`).
The ``Server`` exposes ``getQpNum()``, ``getGid()``, ``getMrAddr()``,
``getMrRkey()`` after this phase.

Steps 3–10: Metadata Bus Handshake
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Performed by ``RoCEv2Server._start()`` directly via the internal metadata
bus helpers:

Each metadata transaction follows the send/response protocol described in
:doc:`../metadata/overview`.  The Python method:

.. code-block:: python

    async def _setup_connection(self, server):
        # Step 3: Allocate PD
        pd_handler = await self._send_alloc_pd(allocOrNot=1)

        # Step 4: Allocate MR
        lkey = await self._send_alloc_mr(
            pdHandler  = pd_handler,
            laddr      = server.getMrAddr(),
            length     = server.getMrLength(),
            accFlags   = ACC_PERM,
            rkey       = server.getMrRkey(),
        )

        # Step 5: Create QP
        fpga_qp_num = await self._send_create_qp(
            pdHandler = pd_handler,
            qpType    = IBV_QPT_RC,
        )

        # Step 6: QP → INIT
        await self._send_qp_init(fpga_qp_num)

        # Step 7: FPGA QP → RTR
        await self._send_qp_rtr(
            qpn     = fpga_qp_num,
            dqpn    = server.getQpNum(),  # host QP number
            gid     = server.getGid(),    # host GID
            rqPsn   = 0,
            pathMtu = IBV_MTU_4096,
        )

        # Step 8: Host QP INIT → RTR  (C++ call)
        server.transitionToRtr(fpga_qp_num, fpga_gid)

        # Step 9: FPGA QP → RTS
        await self._send_qp_rts(
            qpn      = fpga_qp_num,
            sqPsn    = 0,
            retryCnt = DEFAULT_RETRY_NUM,
            rnrRetry = DEFAULT_RETRY_NUM,
            timeout  = DEFAULT_TIMEOUT,
        )

        # Step 10: Host QP RTR → RTS  (C++ call)
        server.transitionToRts()

Step 11: WorkReqDispatcher Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After the QP handshake, the host writes the MR parameters into the FPGA's
WorkReqDispatcher so it knows where to write::

    engine.RAddr.set(server.getMrAddr())
    engine.RKey.set(server.getMrRkey())
    engine.AddrWrapCount.set(rxQueueDepth)
    engine.FrameLen.set(maxPayload)

Steps 12–13: Steady-State Operation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once both QPs are in RTS:

* The FPGA generates RDMA WRITE-with-Immediate work requests targeting the
  host MR base address, cycling through slots.
* The host CQ polling thread receives completions and delivers frames to
  the rogue stream pipeline.
* No host CPU involvement occurs on the data path — only on CQE delivery.

Error Handling
--------------

If any metadata bus transaction fails (``successOrNot = 0`` in the
response), ``_setup_connection()`` raises a ``RoceConnectionError`` with
the failing step name.  ``RoCEv2Server._start()`` propagates this as a
rogue startup error.

If the host QP transitions fail (``ibv_modify_qp`` returns non-zero),
the C++ layer throws a ``rogue::GeneralError``.

Retry behaviour on the data path is governed by the FPGA's ``retry_cnt``
and ``rnr_retry`` QP attributes set in step 9, and by DCQCN for congestion
(see :doc:`../dcqcn/overview`).
