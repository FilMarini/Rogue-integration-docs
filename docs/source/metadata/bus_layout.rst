Bus Layout Reference
====================

This page gives the exact bit layout of every field across all message types.
All fields are packed **LSB-first**: field 0 starts at bit 0, each successive
field is placed immediately above the previous one.  The ``busType`` tag
always occupies the two most-significant bits of the bus.

Constant Definitions
--------------------

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
     - ``log2(MAX_PD)``
     - Bits to index Protection Domains.  ``MAX_PD = 1``, so
       ``PD_INDEX_B = 0``.
   * - ``PD_ALLOC_OR_NOT_B``
     - 1
     - Allocate (1) or free (0) flag
   * - ``PD_HANDLER_B``
     - 32
     - PD handler width
   * - ``PD_KEY_B``
     - ``PD_HANDLER_B − PD_INDEX_B``
     - PD key width
   * - ``MR_INDEX_B``
     - ``log2(MAX_MR / MAX_PD)``
     - Bits to index MRs per PD
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
     - ``MR_KEY_B − MR_INDEX_B``
     - lkey partial
   * - ``MR_RKEYPART_B``
     - ``MR_KEY_B − MR_INDEX_B``
     - rkey partial
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
     - Expected current QP state
   * - ``QPA_PMTU_B``
     - 3
     - Path MTU (``IBV_MTU_4096 = 5``)
   * - ``QPA_QKEY_B``
     - 32
     - Q-Key (RC: set to 0)
   * - ``QPA_RQPSN_B``
     - 24
     - Receive/remote starting PSN
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
   * - ``QPA_MAXDESTREADATOMIC_B``
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
     - Request sub-type (0=create, 1=destroy, 2=modify, 3=query)
   * - ``QP_PDHANDLER_B``
     - 32
     - PD handler for QP create
   * - ``QP_QPN_B``
     - 24
     - QP number
   * - ``QP_ATTRMASK_B``
     - 26
     - Attribute mask
   * - ``QP_ATTR_B``
     - 212
     - Total QP attribute payload width
   * - ``QP_INITATTR_B``
     - 5
     - Init attribute width (``QPI_TYPE_B + QPI_SQSIGALL_B``)

QP Attribute Bus (212 bits, LSB-first)
----------------------------------------

The ``attr`` field used in QP modify requests.  Bit positions are
relative to bit 0 of the ``attr`` block (= bit 84 of the full TX bus).

.. list-table::
   :header-rows: 1
   :widths: 25 15 10 50

   * - Field
     - Bits (within ``attr``)
     - Width
     - Description
   * - ``qpaRnrRetry``
     - ``[2:0]``
     - 3
     - RNR retry count
   * - ``qpaRetryCnt``
     - ``[5:3]``
     - 3
     - Retry count
   * - ``qpaTimeOut``
     - ``[10:6]``
     - 5
     - Local ACK timeout
   * - ``qpaRnrTimer``
     - ``[15:11]``
     - 5
     - RNR NAK timer
   * - ``qpaMaxDestReadAtomic``
     - ``[23:16]``
     - 8
     - Max incoming RDMA read/atomic
   * - ``qpaMaxReadAtomic``
     - ``[31:24]``
     - 8
     - Max outstanding RDMA read/atomic
   * - ``qpaSqDraining``
     - ``[32:32]``
     - 1
     - SQ draining flag
   * - ``qpaPKey``
     - ``[48:33]``
     - 16
     - Partition key
   * - ``qpaCap``
     - ``[88:49]``
     - 40
     - QP capabilities word
   * - ``qpaAccFlags``
     - ``[96:89]``
     - 8
     - QP access flags
   * - ``qpaDqpn``
     - ``[120:97]``
     - 24
     - Destination QP number
   * - ``qpaSqPsn``
     - ``[144:121]``
     - 24
     - Send starting PSN
   * - ``qpaRqPsn``
     - ``[168:145]``
     - 24
     - Receive starting PSN
   * - ``qpaQKey``
     - ``[200:169]``
     - 32
     - Q-Key
   * - ``qpaPmtu``
     - ``[203:201]``
     - 3
     - Path MTU
   * - ``qpaCurrQpState``
     - ``[207:204]``
     - 4
     - Expected current QP state
   * - ``qpaQpState``
     - ``[211:208]``
     - 4
     - Target QP state

QP Init Attribute Bus (5 bits, LSB-first)
------------------------------------------

Bit positions relative to bit 0 of the ``initAttr`` block
(= bit 296 of the full TX bus).

.. list-table::
   :header-rows: 1
   :widths: 25 15 10 50

   * - Field
     - Bits (within ``initAttr``)
     - Width
     - Description
   * - ``qpiSqSigAll``
     - ``[0:0]``
     - 1
     - Signal all send completions
   * - ``qpiType``
     - ``[4:1]``
     - 4
     - QP type (``IBV_QPT_RC = 2``)

Access Permissions (``accFlags``)
----------------------------------

.. list-table::
   :header-rows: 1
   :widths: 10 15 75

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

For the host MR (target of FPGA WRITEs), use ``ACC_PERM = 0x0F``.

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
   * - 8
     - ``IBV_QPS_CREATE``
     - Created (firmware internal state)

QP Request Type Encoding
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - Value
     - Name
     - Description
   * - 0
     - ``REQ_QP_CREATE``
     - Create a new QP
   * - 1
     - ``REQ_QP_DESTROY``
     - Destroy an existing QP
   * - 2
     - ``REQ_QP_MODIFY``
     - Modify QP attributes / state
   * - 3
     - ``REQ_QP_QUERY``
     - Query current QP state

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
     - 4096 (recommended for 10 GbE)
