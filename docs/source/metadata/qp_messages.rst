QP Messages (Queue Pair)
========================

Queue Pair messages create, modify, and transition the FPGA's internal QP
through its state machine.  The bus type tag is ``0b10`` (value ``2``).

A QP message carries a **request sub-type** (``reqType``) field that
distinguishes create from modify:

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - ``reqType``
     - Name
     - Description
   * - ``0b00``
     - Create
     - Create a new QP.  Supply ``pdHandler`` and ``initAttr``.
   * - ``0b01``
     - Modify
     - Modify an existing QP.  Supply ``qpn``, ``attrMask``, ``attr``.

QP Create Request
-----------------

Field layout for ``reqType = 0b00``:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Field
     - Width (bits)
     - Description
   * - ``reqType``
     - 2
     - ``0b00``
   * - ``pdHandler``
     - 32
     - PD handler (from PD allocation response)
   * - ``qpn``
     - 24
     - Desired QP number.  Pass ``0`` to let the FPGA assign.
   * - ``attrMask``
     - 26
     - Set bits indicate which ``attr`` fields are valid.  For create,
       only ``initAttr`` fields are used.
   * - ``initAttr``
     - 5
     - ``qpType(4b) | sqSigAll(1b)``

Total payload: ``2 + 32 + 24 + 26 + 5 = 89 bits``

Padding: ``303 − 2 − 89 = 212 bits``

TX bus layout (create):

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Bits [302:0]
     - Field
     - Notes
   * - ``[302:301]``
     - ``busType``
     - ``0b10``
   * - ``[300:214]``
     - padding
     - zeros (87 bits)
   * - ``[213:212]``
     - ``reqType``
     - ``0b00``
   * - ``[211:180]``
     - ``pdHandler``
     - 32 bits
   * - ``[179:156]``
     - ``qpn``
     - 24 bits (0 = FPGA-assigned)
   * - ``[155:130]``
     - ``attrMask``
     - 26 bits
   * - ``[129:125]``
     - ``initAttr``
     - 5 bits: ``qpType[3:0] | sqSigAll``
   * - ``[124:0]``
     - padding
     - remaining zeros

Python encoder (create):

.. code-block:: python

    BUS_TYPE_QP = 0b10
    IBV_QPT_RC  = 2

    def encode_create_qp(pd_handler: int, qp_type: int = IBV_QPT_RC,
                         sq_sig_all: int = 0, qpn: int = 0,
                         attr_mask: int = 0) -> int:
        init_attr = (qp_type << 1) | sq_sig_all
        return (
            (BUS_TYPE_QP << 301) |
            (0b00        << 212) |   # reqType = create
            (pd_handler  << 180) |
            (qpn         << 156) |
            (attr_mask   << 130) |
            (init_attr   << 125)
        )

QP Modify Request
-----------------

For state transitions (INIT, RTR, RTS), ``reqType = 0b01`` is used.
The ``attr`` field is a 212-bit packed structure of QP attributes.
The ``attrMask`` indicates which attributes are present.

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Field
     - Width (bits)
     - Description
   * - ``reqType``
     - 2
     - ``0b01``
   * - ``pdHandler``
     - 32
     - PD handler (same as used at create time)
   * - ``qpn``
     - 24
     - QP number (from create response)
   * - ``attrMask``
     - 26
     - Bitmask of valid attribute fields (see below)
   * - ``attr``
     - 212
     - Packed QP attribute structure (see below)

The ``attr`` field (212 bits, packed MSB-first):

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Width (bits)
     - Description
   * - ``qpState``
     - 4
     - Target state (see :doc:`bus_layout` §QP State Encoding)
   * - ``curQpState``
     - 4
     - Expected current state (0 = don't check)
   * - ``pathMtu``
     - 3
     - Path MTU (5 = ``IBV_MTU_4096``)
   * - ``qKey``
     - 32
     - Q-Key (RC: unused, set to 0)
   * - ``rqPsn``
     - 24
     - Receive/remote starting PSN (used in RTR)
   * - ``sqPsn``
     - 24
     - Send starting PSN (used in RTS)
   * - ``dqpn``
     - 24
     - Destination QP number (host QP num, used in RTR)
   * - ``qpAccFlags``
     - 8
     - QP access flags
   * - ``cap``
     - 40
     - Capabilities word (see ``CAP_VALUE`` in firmware)
   * - ``pkey``
     - 16
     - Partition key (0 for RoCEv2)
   * - ``sqDraining``
     - 1
     - SQ draining flag (set during SQD transitions)
   * - ``maxReadAtomic``
     - 8
     - Max outstanding RDMA READ/ATOMIC (initiator side)
   * - ``maxDestRd``
     - 8
     - Max incoming RDMA READ/ATOMIC (responder side)
   * - ``rnrTimer``
     - 5
     - RNR NAK timer (FPGA side wait)
   * - ``timeout``
     - 5
     - Local ACK timeout (conservative: 14 ≈ 4 s)
   * - ``retryCnt``
     - 3
     - Retry count on local errors
   * - ``rnrRetry``
     - 3
     - Retry count on RNR NAK

Total ``attr`` width: ``4+4+3+32+24+24+24+8+40+16+1+8+8+5+5+3+3 = 212`` ✓

``attrMask`` Bit Positions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``attrMask`` mirrors the ``ibv_qp_attr_mask`` enum.  Key values:

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - Bit
     - Hex mask
     - Attribute
   * - 0
     - ``0x000001``
     - ``IBV_QP_STATE``
   * - 1
     - ``0x000002``
     - ``IBV_QP_CUR_STATE``
   * - 2
     - ``0x000004``
     - ``IBV_QP_EN_SQD_ASYNC_NOTIFY``
   * - 3
     - ``0x000008``
     - ``IBV_QP_ACCESS_FLAGS``
   * - 4
     - ``0x000010``
     - ``IBV_QP_PKEY_INDEX``
   * - 5
     - ``0x000020``
     - ``IBV_QP_PORT``
   * - 6
     - ``0x000040``
     - ``IBV_QP_QKEY``
   * - 7
     - ``0x000080``
     - ``IBV_QP_AV``
   * - 8
     - ``0x000100``
     - ``IBV_QP_PATH_MTU``
   * - 9
     - ``0x000200``
     - ``IBV_QP_TIMEOUT``
   * - 10
     - ``0x000400``
     - ``IBV_QP_RETRY_CNT``
   * - 11
     - ``0x000800``
     - ``IBV_QP_RNR_RETRY``
   * - 12
     - ``0x001000``
     - ``IBV_QP_RQ_PSN``
   * - 13
     - ``0x002000``
     - ``IBV_QP_MAX_QP_RD_ATOMIC``
   * - 14
     - ``0x004000``
     - ``IBV_QP_ALT_PATH``
   * - 15
     - ``0x008000``
     - ``IBV_QP_MIN_RNR_TIMER``
   * - 16
     - ``0x010000``
     - ``IBV_QP_SQ_PSN``
   * - 17
     - ``0x020000``
     - ``IBV_QP_MAX_DEST_RD_ATOMIC``
   * - 18
     - ``0x040000``
     - ``IBV_QP_PATH_MIG_STATE``
   * - 19
     - ``0x080000``
     - ``IBV_QP_CAP``
   * - 20
     - ``0x100000``
     - ``IBV_QP_DEST_QPN``

Per-Transition Attribute Masks and Values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**QP INIT** (RESET → INIT):

.. code-block:: python

    INIT_MASK  = IBV_QP_STATE | IBV_QP_ACCESS_FLAGS | IBV_QP_PKEY_INDEX | IBV_QP_PORT
    # = 0x000001 | 0x000008 | 0x000010 | 0x000020 = 0x000039

    attr.qpState    = IBV_QPS_INIT  # 1
    attr.qpAccFlags = IBV_ACCESS_REMOTE_WRITE  # 0x02

**QP RTR** (INIT → RTR):

.. code-block:: python

    RTR_MASK = (IBV_QP_STATE | IBV_QP_AV | IBV_QP_PATH_MTU | IBV_QP_DEST_QPN |
                IBV_QP_RQ_PSN | IBV_QP_MAX_DEST_RD_ATOMIC | IBV_QP_MIN_RNR_TIMER)
    # = 0x021381

    attr.qpState      = IBV_QPS_RTR   # 2
    attr.pathMtu      = IBV_MTU_4096  # 5
    attr.dqpn         = host_qp_num   # host QP number (from C++ Server)
    attr.rqPsn        = 0
    attr.maxDestRd    = MAX_QP_RD_ATOM  # 16
    attr.rnrTimer     = DEFAULT_RNR_TIMER  # 1
    # av (address vector / GID) is embedded in the attr structure

**QP RTS** (RTR → RTS):

.. code-block:: python

    RTS_MASK = (IBV_QP_STATE | IBV_QP_TIMEOUT | IBV_QP_RETRY_CNT |
                IBV_QP_RNR_RETRY | IBV_QP_SQ_PSN | IBV_QP_MAX_QP_RD_ATOMIC)
    # = 0x010E01

    attr.qpState    = IBV_QPS_RTS  # 3
    attr.sqPsn      = 0
    attr.timeout    = DEFAULT_TIMEOUT   # 14
    attr.retryCnt   = DEFAULT_RETRY_NUM  # 3
    attr.rnrRetry   = DEFAULT_RETRY_NUM  # 3
    attr.maxReadAtomic = 0

.. note::
   ``rnr_retry`` and ``retry_cnt`` in this context are set on the **FPGA's**
   QP via the metadata bus.  They govern how many times the FPGA retransmits
   when it receives an RNR NAK or a timeout from the host.

   The host's own ``min_rnr_timer`` (set via ``ibv_modify_qp`` on the host
   QP during INIT→RTR) communicates to the FPGA the minimum delay it must
   wait before retrying after the host sends an RNR NAK.

QP Response (RX bus)
---------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Bits [275:0]
     - Field
     - Description
   * - ``[275:274]``
     - ``busType``
     - ``0b10``
   * - ``[273]``
     - ``successOrNot``
     - ``1`` = success
   * - ``[272:249]``
     - ``qpn``
     - 24-bit QP number assigned by the FPGA (create) or echoed (modify)
   * - ``[248:245]``
     - ``qpState``
     - 4-bit current QP state after the operation
   * - ``[244:0]``
     - padding
     - zeros

Python Decoder
~~~~~~~~~~~~~~

.. code-block:: python

    def decode_qp_resp(rx: int) -> tuple[bool, int, int]:
        """Return (success, qpn, qp_state)."""
        success  = bool((rx >> (META_DATA_RX_BITS - 3)) & 1)
        qpn      = (rx >> (META_DATA_RX_BITS - 3 - 24)) & 0xFFFFFF
        qp_state = (rx >> (META_DATA_RX_BITS - 3 - 24 - 4)) & 0xF
        return success, qpn, qp_state
