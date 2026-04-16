Bus Layout Reference
====================

This page gives the exact bit layout of every field across all message types.
All positions are given as bit indices within the full 303-bit TX bus or
276-bit RX bus, with bit 302 (TX) / bit 275 (RX) being the most significant.

Constant Definitions
--------------------

The following constants appear throughout the field tables.  They are defined
in the pyrogue layer and in the FPGA firmware.

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Constant
     - Value
     - Description
   * - ``META_DATA_BITS``
     - 303
     - Total width of the TX metadata bus
   * - ``META_DATA_RX_BITS``
     - 276
     - Total width of the RX metadata bus
   * - ``PD_INDEX_B``
     - 3
     - Bits to index ``MAX_PD`` Protection Domains.  Note: the engine
       currently supports ``MAX_PD = 1``; only one PD can be active at
       a time.
   * - ``PD_ALLOC_OR_NOT_B``
     - 1
     - Allocate (1) or free (0) flag
   * - ``PD_HANDLER_B``
     - 32
     - PD handler width
   * - ``PD_KEY_B``
     - 29
     - PD key width (``PD_HANDLER_B – PD_INDEX_B``)
   * - ``MR_INDEX_B``
     - 4
     - Bits to index ``MAX_MR_PER_PD = 16``
   * - ``MR_ALLOC_OR_NOT_B``
     - 1
     - Allocate (1) or free (0) flag
   * - ``MR_LADDR_B``
     - 64
     - Memory Region local virtual address width
   * - ``MR_LEN_B``
     - 32
     - Memory Region length width
   * - ``MR_ACCFLAGS_B``
     - 8
     - Access flags width
   * - ``MR_PDHANDLER_B``
     - 32
     - PD handler associated with the MR
   * - ``MR_KEY_B``
     - 32
     - lkey / rkey width
   * - ``MR_LKEYPART_B``
     - 28
     - lkey partial (``MR_KEY_B – MR_INDEX_B``)
   * - ``MR_RKEYPART_B``
     - 28
     - rkey partial (``MR_KEY_B – MR_INDEX_B``)
   * - ``MR_LKEYORNOT_B``
     - 1
     - 1 = allocate lkey, 0 = skip
   * - ``QPI_TYPE_B``
     - 4
     - QP type (``IBV_QPT_RC = 2``)
   * - ``QPI_SQSIGALL_B``
     - 1
     - Signal all send completions flag
   * - ``QPA_QPSTATE_B``
     - 4
     - Target QP state
   * - ``QPA_CURRQPSTATE_B``
     - 4
     - Expected current QP state (0 = don't care)
   * - ``QPA_PMTU_B``
     - 3
     - Path MTU (``IBV_MTU_4096 = 5``)
   * - ``QPA_QKEY_B``
     - 32
     - Q-Key (RC QPs: unused, set to 0)
   * - ``QPA_RQPSN_B``
     - 24
     - Remote/receive starting PSN
   * - ``QPA_SQPSN_B``
     - 24
     - Send starting PSN
   * - ``QPA_DQPN_B``
     - 24
     - Destination QP number
   * - ``QPA_QPACCFLAGS_B``
     - 8
     - QP access flags
   * - ``QPA_CAP_B``
     - 40
     - QP capabilities word
   * - ``QPA_PKEY_B``
     - 16
     - Partition key
   * - ``QPA_SQDRAINING_B``
     - 1
     - SQ draining flag
   * - ``QPA_MAXREADATOMIC_B``
     - 8
     - Max outstanding RDMA read/atomic (initiator)
   * - ``QPA_MAXDESTRD_B``
     - 8
     - Max incoming RDMA read/atomic (responder)
   * - ``QPA_RNRTIMER_B``
     - 5
     - RNR NAK timer
   * - ``QPA_TIMEOUT_B``
     - 5
     - Local ACK timeout
   * - ``QPA_RETRYCNT_B``
     - 3
     - Retry count
   * - ``QPA_RNRRETRY_B``
     - 3
     - RNR retry count
   * - ``QP_REQTYPE_B``
     - 2
     - Request sub-type (0=create, 1=modify)
   * - ``QP_PDHANDLER_B``
     - 32
     - PD handler for QP create
   * - ``QP_QPN_B``
     - 24
     - QP number
   * - ``QP_ATTRMASK_B``
     - 26
     - Attribute mask (which fields are valid)
   * - ``QP_ATTR_B``
     - 212
     - Total QP attribute payload width
   * - ``QP_INITATTR_B``
     - 5
     - Init attribute width (``QPI_TYPE_B + QPI_SQSIGALL_B``)

TX Bus Map (303 bits)
----------------------

The bus is transmitted as a Python integer.  Bit 302 is the MSB.

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Bits
     - Field
     - Notes
   * - ``[302:301]``
     - ``busType``
     - 0=PD, 1=MR, 2=QP
   * - ``[300:N+1]``
     - padding
     - Zero-filled.  Size depends on message type.
   * - ``[N:0]``
     - payload
     - Message-specific fields, packed MSB-first

RX Bus Map (276 bits)
----------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Bits
     - Field
     - Notes
   * - ``[275:274]``
     - ``busType``
     - Echoes the request bus type
   * - ``[273]``
     - ``successOrNot``
     - 1 = success, 0 = failure
   * - ``[272:0]``
     - payload
     - Message-specific response fields

Access Permissions (``accFlags``)
----------------------------------

The ``accFlags`` byte in MR and QP messages uses the IB access flag encoding:

.. list-table::
   :header-rows: 1
   :widths: 15 15 70

   * - Bit
     - Mask
     - Meaning
   * - 0
     - ``0x01``
     - ``IBV_ACCESS_LOCAL_WRITE``
   * - 1
     - ``0x02``
     - ``IBV_ACCESS_REMOTE_WRITE``
   * - 2
     - ``0x04``
     - ``IBV_ACCESS_REMOTE_READ``
   * - 3
     - ``0x08``
     - ``IBV_ACCESS_REMOTE_ATOMIC``

For the host MR (target of FPGA WRITEs), the recommended flags are
``ACC_PERM = 0x0F`` (all four permissions).

QP State Encoding
------------------

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - Value
     - Name
     - Description
   * - 0
     - ``IBV_QPS_RESET``
     - Initial state after create
   * - 1
     - ``IBV_QPS_INIT``
     - Initialized
   * - 2
     - ``IBV_QPS_RTR``
     - Ready To Receive
   * - 3
     - ``IBV_QPS_RTS``
     - Ready To Send (and receive)
   * - 4
     - ``IBV_QPS_SQD``
     - Send Queue Draining
   * - 5
     - ``IBV_QPS_SQE``
     - Send Queue Error
   * - 6
     - ``IBV_QPS_ERR``
     - Error

Path MTU Encoding
------------------

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - Value
     - Name
     - Payload bytes
   * - 1
     - ``IBV_MTU_256``
     - 256
   * - 2
     - ``IBV_MTU_512``
     - 512
   * - 3
     - ``IBV_MTU_1024``
     - 1024
   * - 4
     - ``IBV_MTU_2048``
     - 2048
   * - 5
     - ``IBV_MTU_4096``
     - 4096 (recommended for 10 GbE links)
