QP Messages (Queue Pair)
========================

Queue Pair messages create, modify, query, and destroy the FPGA's internal QP.
Bus type tag: ``2`` (``METADATA_QP_T``).

Fields are packed **LSB-first** from bit 0.  ``busType`` is fixed at the
two MSBs of the bus.

QP Request (TX, 303-bit bus)
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Field
     - Bits
     - Width
     - Description
   * - ``reqType``
     - ``[1:0]``
     - 2
     - Operation: ``0``=create, ``1``=destroy, ``2``=modify, ``3``=query.
   * - ``pdHandler``
     - ``[33:2]``
     - 32
     - PD handler from the PD allocation response.
   * - ``qpn``
     - ``[57:34]``
     - 24
     - Target QP number.  Pass ``0`` for create (FPGA assigns).
       For all other operations pass the FPGA-assigned QPN.
   * - ``attrMask``
     - ``[83:58]``
     - 26
     - Bitmask of valid attribute fields in ``attr``.
       See ``IBV_QP_*`` mask values in :doc:`bus_layout`.
   * - ``attr``
     - ``[295:84]``
     - 212
     - QP attribute block (see :ref:`qp-attr-bus` below).
   * - ``initAttr``
     - ``[300:296]``
     - 5
     - QP init attribute block (see :ref:`qp-initattr-bus` below).
       Used for ``REQ_QP_CREATE``.
   * - ``busType``
     - ``[302:301]``
     - 2
     - ``2`` (QP).  Fixed at the two MSBs.

.. _qp-attr-bus:

QP Attribute Block (``attr``, bits [295:84] of TX bus)
-------------------------------------------------------

The 212-bit ``attr`` field is itself packed LSB-first.  The bit positions
below are relative to the start of ``attr`` (i.e. bit 0 of ``attr`` =
bit 84 of the full TX bus).

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
     - RNR retry count (FPGA retries after receiving RNR NAK).
   * - ``qpaRetryCnt``
     - ``[5:3]``
     - 3
     - Retry count (FPGA retries after timeout/sequence error).
   * - ``qpaTimeOut``
     - ``[10:6]``
     - 5
     - Local ACK timeout.
   * - ``qpaRnrTimer``
     - ``[15:11]``
     - 5
     - RNR NAK timer.
   * - ``qpaMaxDestReadAtomic``
     - ``[23:16]``
     - 8
     - Max incoming RDMA read/atomic (responder side).
   * - ``qpaMaxReadAtomic``
     - ``[31:24]``
     - 8
     - Max outstanding RDMA read/atomic (initiator side).
   * - ``qpaSqDraining``
     - ``[32:32]``
     - 1
     - SQ draining flag.
   * - ``qpaPKey``
     - ``[48:33]``
     - 16
     - Partition key.
   * - ``qpaCap``
     - ``[88:49]``
     - 40
     - QP capabilities word.
   * - ``qpaAccFlags``
     - ``[96:89]``
     - 8
     - QP access flags.
   * - ``qpaDqpn``
     - ``[120:97]``
     - 24
     - Destination QP number (host QP number, used in RTR).
   * - ``qpaSqPsn``
     - ``[144:121]``
     - 24
     - Send starting PSN (used in RTS).
   * - ``qpaRqPsn``
     - ``[168:145]``
     - 24
     - Receive starting PSN (used in RTR).
   * - ``qpaQKey``
     - ``[200:169]``
     - 32
     - Q-Key (set to ``0`` for RC QPs).
   * - ``qpaPmtu``
     - ``[203:201]``
     - 3
     - Path MTU (``5`` = ``IBV_MTU_4096``).
   * - ``qpaCurrQpState``
     - ``[207:204]``
     - 4
     - Expected current QP state (``0`` = don't check).
   * - ``qpaQpState``
     - ``[211:208]``
     - 4
     - Target QP state.

.. _qp-initattr-bus:

QP Init Attribute Block (``initAttr``, bits [300:296] of TX bus)
-----------------------------------------------------------------

The 5-bit ``initAttr`` field, also packed LSB-first within its window:

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
     - Signal all send completions (set to ``0``).
   * - ``qpiType``
     - ``[4:1]``
     - 4
     - QP type (``IBV_QPT_RC = 2``).

Per-Transition Attribute Masks and Key Values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**QP INIT** (RESET → INIT):

.. code-block:: python

    attr.qpaQpState  = IBV_QPS_INIT   # 1  → bits [211:208] of attr
    attr.qpaAccFlags = 0x02           # IBV_ACCESS_REMOTE_WRITE

**QP RTR** (INIT → RTR):

.. code-block:: python

    attr.qpaQpState  = IBV_QPS_RTR    # 2
    attr.qpaPmtu     = IBV_MTU_4096   # 5
    attr.qpaDqpn     = host_qp_num    # host QP number
    attr.qpaRqPsn    = host_rq_psn
    attr.qpaRnrTimer = DEFAULT_RNR_TIMER

**QP RTS** (RTR → RTS):

.. code-block:: python

    attr.qpaQpState  = IBV_QPS_RTS    # 3
    attr.qpaSqPsn    = 0
    attr.qpaTimeOut  = DEFAULT_TIMEOUT
    attr.qpaRetryCnt = DEFAULT_RETRY_NUM
    attr.qpaRnrRetry = DEFAULT_RETRY_NUM

.. note::
   ``qpaRnrRetry`` and ``qpaRetryCnt`` govern the **FPGA's** retry
   behaviour.  The host's own ``min_rnr_timer`` (set via ``ibv_modify_qp``
   on the host QP) tells the FPGA the minimum delay before retrying after
   sending an RNR NAK.

QP Response (RX, 276-bit bus)
------------------------------

All fields are at fixed absolute positions within the 276-bit bus,
taken directly from the ``respQp`` class:

.. list-table::
   :header-rows: 1
   :widths: 25 15 10 50

   * - Field
     - Bits
     - Width
     - Description
   * - ``qpiSqSigAll``
     - ``[0:0]``
     - 1
     - Signal-all flag.
   * - ``qpiType``
     - ``[4:1]``
     - 4
     - QP type.
   * - ``qpaRnrRetry``
     - ``[7:5]``
     - 3
     - RNR retry count.
   * - ``qpaRetryCnt``
     - ``[10:8]``
     - 3
     - Retry count.
   * - ``qpaTimeOut``
     - ``[15:11]``
     - 5
     - Local ACK timeout.
   * - ``qpaRnrTimer``
     - ``[20:16]``
     - 5
     - RNR NAK timer.
   * - ``qpaMaxDestReadAtomic``
     - ``[28:21]``
     - 8
     - Max incoming RDMA read/atomic.
   * - ``qpaMaxReadAtomic``
     - ``[36:29]``
     - 8
     - Max outstanding RDMA read/atomic.
   * - ``qpaSqDraining``
     - ``[37:37]``
     - 1
     - SQ draining flag.
   * - ``qpaPKey``
     - ``[53:38]``
     - 16
     - Partition key.
   * - ``qpaCap``
     - ``[93:54]``
     - 40
     - QP capabilities word.
   * - ``qpaAccFlags``
     - ``[101:94]``
     - 8
     - QP access flags.
   * - ``qpaDqpn``
     - ``[125:102]``
     - 24
     - Destination QP number.
   * - ``qpaSqPsn``
     - ``[149:126]``
     - 24
     - Send starting PSN.
   * - ``qpaRqPsn``
     - ``[173:150]``
     - 24
     - Receive starting PSN.
   * - ``qpaQKey``
     - ``[205:174]``
     - 32
     - Q-Key.
   * - ``qpaPmtu``
     - ``[208:206]``
     - 3
     - Path MTU.
   * - ``qpaCurrQpState``
     - ``[212:209]``
     - 4
     - Current QP state (before the operation).
   * - ``qpaQpState``
     - ``[216:213]``
     - 4
     - Target QP state (after the operation).
   * - ``pdHandler``
     - ``[248:217]``
     - 32
     - PD handler.
   * - ``qpn``
     - ``[272:249]``
     - 24
     - FPGA-assigned QP number.  Save this and use it for all
       subsequent modify/destroy/query requests.
   * - ``successOrNot``
     - ``[273:273]``
     - 1
     - ``1`` = success, ``0`` = failure.
   * - ``busType``
     - ``[275:274]``
     - 2
     - ``2`` — echoes QP request type.  Fixed at the two MSBs.

Python decoder for the most-used fields:

.. code-block:: python

    qpn          = (rx >> 249) & 0xFFFFFF
    successOrNot = (rx >> 273) & 1
    qpaQpState   = (rx >> 213) & 0xF
    pdHandler    = (rx >> 217) & 0xFFFFFFFF
    busType      = (rx >> 274) & 0x3
