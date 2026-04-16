Host-Side Setup
===============

This page describes what the host software does during startup and steady-state
operation.  Everything here happens inside ``rogue.protocols.rocev2``.

libibverbs Resource Allocation
--------------------------------

The C++ ``Server`` constructor allocates the following libibverbs resources
in order:

1. **Open device** — ``ibv_open_device()`` on the requested RDMA device
   (e.g. ``mlx5_0``).  Use ``ibv_get_device_list()`` / ``ibv_devices`` to
   enumerate available devices.

2. **Allocate Protection Domain** — ``ibv_alloc_pd()``.  All subsequent
   resources are associated with this PD.

3. **Register Memory Region** — a single contiguous slab::

       size  = rxQueueDepth × maxPayload
       flags = IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_REMOTE_WRITE

   The resulting ``ibv_mr`` provides ``addr`` and ``rkey`` that must be
   communicated to the FPGA (see :doc:`connection_flow`).

4. **Create Completion Queue** — ``ibv_create_cq()`` with at least
   ``rxQueueDepth`` entries.

5. **Create Queue Pair** (RC type)::

       ibv_qp_init_attr attr = {
           .send_cq = cq,
           .recv_cq = cq,
           .qp_type = IBV_QPT_RC,
           .cap = {
               .max_recv_wr  = rxQueueDepth,
               .max_recv_sge = 1,
               .max_send_wr  = 0,   // receive-only QP
           },
       };

   .. note::
      The QP is receive-only.  The FPGA is the WRITE initiator;
      the host never posts SEND work requests.

QP State Transitions
---------------------

The QP is transitioned through the standard RC state machine:

RESET → INIT
~~~~~~~~~~~~~

.. code-block:: c

    ibv_qp_attr attr = {
        .qp_state   = IBV_QPS_INIT,
        .pkey_index = 0,
        .port_num   = 1,
        .qp_access_flags = IBV_ACCESS_REMOTE_WRITE,
    };
    ibv_modify_qp(qp, &attr,
        IBV_QP_STATE | IBV_QP_PKEY_INDEX |
        IBV_QP_PORT  | IBV_QP_ACCESS_FLAGS);

INIT → RTR (Ready To Receive)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This transition requires the **FPGA's** QP number and GID, which are obtained
from the FPGA via the metadata bus handshake:

.. code-block:: c

    ibv_qp_attr attr = {
        .qp_state           = IBV_QPS_RTR,
        .path_mtu           = IBV_MTU_4096,
        .dest_qp_num        = fpga_qp_num,    // from FPGA
        .rq_psn             = 0,
        .max_dest_rd_atomic = 16,
        .min_rnr_timer      = 1,              // min wait before RNR NAK
        .ah_attr = {
            .is_global  = 1,
            .grh = {
                .dgid       = fpga_gid,       // ::ffff:<fpga_ip>
                .sgid_index = 0,
                .hop_limit  = 64,
            },
            .port_num = 1,
        },
    };
    ibv_modify_qp(qp, &attr,
        IBV_QP_STATE | IBV_QP_AV | IBV_QP_PATH_MTU |
        IBV_QP_DEST_QPN | IBV_QP_RQ_PSN |
        IBV_QP_MAX_DEST_RD_ATOMIC | IBV_QP_MIN_RNR_TIMER);

.. important::
   ``min_rnr_timer`` is set on the **host** QP.  It tells the FPGA the
   minimum time (in units defined by the IB spec) the host needs before it
   can accept a retransmit after sending an RNR NAK.  The FPGA's own retry
   parameters (``rnr_retry``, ``retry_cnt``) are set via the metadata bus
   (see :doc:`../metadata/qp_messages`).

RTR → RTS (Ready To Send)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: c

    ibv_qp_attr attr = {
        .qp_state      = IBV_QPS_RTS,
        .sq_psn        = 0,
        .timeout       = 14,    // ~4 s, conservative for FPGA links
        .retry_cnt     = 3,
        .rnr_retry     = 3,
        .max_rd_atomic = 0,
    };
    ibv_modify_qp(qp, &attr,
        IBV_QP_STATE | IBV_QP_SQ_PSN | IBV_QP_TIMEOUT |
        IBV_QP_RETRY_CNT | IBV_QP_RNR_RETRY |
        IBV_QP_MAX_QP_RD_ATOMIC);

GID Derivation
--------------

The FPGA GID is derived deterministically from the FPGA IP address using the
**IPv4-mapped IPv6** format::

    FPGA IP = 192.168.1.10
    FPGA GID = ::ffff:192.168.1.10
             = 0000:0000:0000:0000:0000:ffff:c0a8:010a

This matches the pattern used in SLAC's root file templates and avoids
requiring a separate GID discovery step.

CQ Polling Thread
-----------------

After the QP reaches RTS, the server spawns a background thread::

    while (running) {
        n = ibv_poll_cq(cq, BATCH_SIZE, wc_array);
        for (i in 0..n) {
            if (wc_array[i].opcode != IBV_WC_RECV_RDMA_WITH_IMM)
                continue;
            channel_id = (wc_array[i].imm_data >> 24) & 0xFF;
            offset     = slot_index * maxPayload;
            length     = wc_array[i].byte_len;
            // build Frame from slab[offset .. offset+length]
            // set firstUser = 0x2 (SSI SOF)
            sendFrame(channel_id, frame);
        }
    }

The polling thread uses a **busy-poll with exponential back-off** to keep
latency low under light load without consuming a full CPU core at idle.
