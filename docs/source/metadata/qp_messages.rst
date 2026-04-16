QP Messages (Queue Pair)
========================

Queue Pair messages create, modify, query, and destroy the FPGA's internal
QP.  The bus type tag is ``2`` (``METADATA_QP_T``).

Fields are packed **LSB-first** from bit 0.  The ``busType`` sits at the
two MSBs ([302:301] TX, [275:274] RX).

The 2-bit ``reqType`` field (``QP_REQTYPE_B``) selects the operation:

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - Value
     - Name
     - Description
   * - ``0``
     - ``REQ_QP_CREATE``
     - Create a new QP.
   * - ``1``
     - ``REQ_QP_DESTROY``
     - Destroy an existing QP.
   * - ``2``
     - ``REQ_QP_MODIFY``
     - Modify QP attributes / drive a state transition.
   * - ``3``
     - ``REQ_QP_QUERY``
     - Query current QP state and attributes.

QP Request (TX bus) — general structure
-----------------------------------------

The TX bus carries ``reqType``, the target ``pdHandler``, the ``qpn``,
an ``attrMask``, an ``attr`` block (212 bits, see :doc:`bus_layout` §QP
Attribute Bus), and an ``initAttr`` block (5 bits), packed from bit 0:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Width (bits)
     - Description
   * - ``reqType``
     - 2
     - Operation type (0=create, 1=destroy, 2=modify, 3=query).
   * - ``pdHandler``
     - 32
     - PD handler returned by the PD allocation response.
   * - ``qpn``
     - 24
     - Target QP number.  Pass ``0`` for create (FPGA assigns).
       Pass the FPGA-assigned QPN for all other operations.
   * - ``attrMask``
     - 26
     - Bitmask of valid attribute fields in ``attr``.
       See ``IBV_QP_*`` mask values in :doc:`bus_layout`.
   * - ``attr``
     - 212
     - QP attribute block, packed LSB-first (see :doc:`bus_layout`
       §QP Attribute Bus).  Fields not covered by ``attrMask`` are
       ignored by the FPGA.
   * - ``initAttr``
     - 5
     - QP init attribute block, packed LSB-first:
       ``qpiSqSigAll`` at bit 0, ``qpiType`` at bits [4:1].
       Used for ``REQ_QP_CREATE``.
   * - ``busType``
     - 2
     - ``2`` (QP).  Always at bits [302:301].

Per-Transition Attribute Masks and Values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**QP INIT** (RESET → INIT) — key ``attr`` fields:

.. code-block:: python

    attr.qpaQpState    = IBV_QPS_INIT   # 1
    attr.qpaAccFlags   = IBV_ACCESS_REMOTE_WRITE  # 0x02
    attrMask           = IBV_QP_STATE | IBV_QP_ACCESS_FLAGS | \
                         IBV_QP_PKEY_INDEX | IBV_QP_PORT

**QP RTR** (INIT → RTR) — key ``attr`` fields:

.. code-block:: python

    attr.qpaQpState    = IBV_QPS_RTR    # 2
    attr.qpaPmtu       = IBV_MTU_4096   # 5
    attr.qpaDqpn       = host_qp_num    # host QP number
    attr.qpaRqPsn      = host_rq_psn
    attr.qpaMaxDestRd  = MAX_QP_RD_ATOM
    attr.qpaRnrTimer   = DEFAULT_RNR_TIMER

**QP RTS** (RTR → RTS) — key ``attr`` fields:

.. code-block:: python

    attr.qpaQpState    = IBV_QPS_RTS    # 3
    attr.qpaSqPsn      = 0
    attr.qpaTimeOut    = DEFAULT_TIMEOUT
    attr.qpaRetryCnt   = DEFAULT_RETRY_NUM
    attr.qpaRnrRetry   = DEFAULT_RETRY_NUM

.. note::
   ``qpaRnrRetry`` and ``qpaRetryCnt`` here are set on the **FPGA's** QP
   and govern how many times the FPGA retransmits when it receives an RNR
   NAK or a timeout from the host.

   The host's own ``min_rnr_timer`` (set via ``ibv_modify_qp`` on the host
   QP during INIT→RTR) communicates to the FPGA the minimum delay it must
   wait before retrying after the host sends an RNR NAK.

QP Response (RX bus)
---------------------

The response is the full echo of the QP state, decoded from bit 0.
From the ``respQp`` class:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Field
     - Bit range
     - Description
   * - ``qpiSqSigAll``
     - ``[0]``
     - Signal-all flag
   * - ``qpiType``
     - ``[4:1]``
     - QP type
   * - ``qpaRnrRetry``
     - ``[7:5]``
     - RNR retry count
   * - ``qpaRetryCnt``
     - ``[10:8]``
     - Retry count
   * - ``qpaTimeOut``
     - ``[15:11]``
     - Local ACK timeout
   * - ``qpaRnrTimer``
     - ``[20:16]``
     - RNR NAK timer
   * - ``qpaMaxDestReadAtomic``
     - ``[28:21]``
     - Max incoming RDMA read/atomic
   * - ``qpaMaxReadAtomic``
     - ``[36:29]``
     - Max outstanding RDMA read/atomic
   * - ``qpaSqDraining``
     - ``[37]``
     - SQ draining flag
   * - ``qpaPKey``
     - ``[53:38]``
     - Partition key
   * - ``qpaCap``
     - ``[93:54]``
     - QP capabilities word
   * - ``qpaAccFlags``
     - ``[101:94]``
     - QP access flags
   * - ``qpaDqpn``
     - ``[125:102]``
     - Destination QP number
   * - ``qpaSqPsn``
     - ``[149:126]``
     - Send starting PSN
   * - ``qpaRqPsn``
     - ``[173:150]``
     - Receive starting PSN
   * - ``qpaQKey``
     - ``[205:174]``
     - Q-Key
   * - ``qpaPmtu``
     - ``[208:206]``
     - Path MTU
   * - ``qpaCurrQpState``
     - ``[212:209]``
     - Current QP state (before the operation)
   * - ``qpaQpState``
     - ``[216:213]``
     - Target QP state (after the operation)
   * - ``pdHandler``
     - ``[248:217]``
     - PD handler
   * - ``qpn``
     - ``[272:249]``
     - QP number (FPGA-assigned; use this for all subsequent operations)
   * - ``successOrNot``
     - ``[273]``
     - ``1`` = success, ``0`` = failure
   * - ``busType``
     - ``[275:274]``
     - ``2`` — echoes QP request type

The two most important fields on a create response are ``qpn`` (which must
be saved and used in all subsequent modify/destroy requests) and
``successOrNot``.
