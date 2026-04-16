MR Messages (Memory Region)
============================

Memory Region messages register or deregister a memory region in the FPGA's
internal resource manager.  The bus type tag is ``1`` (``METADATA_MR_T``).

Fields are packed **LSB-first** from bit 0.  The ``busType`` sits at the
two MSBs ([302:301] TX, [275:274] RX).

MR Request (TX bus)
--------------------

The TX request fields are packed from bit 0 in this order (exact field
ordering mirrors the PD/QP convention — LSB-first, no padding):

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Field
     - Width (bits)
     - Description
   * - ``allocOrNot``
     - 1
     - ``1`` = register (allocate), ``0`` = deregister (free).
   * - ``laddr``
     - 64
     - Host virtual address of the memory region (``ibv_mr.addr``).
   * - ``len``
     - 32
     - Byte length of the memory region.
   * - ``accFlags``
     - 8
     - Access permissions.  Use ``0x0F`` for the FPGA-target MR
       (local write + remote write + remote read + remote atomic).
       See :doc:`bus_layout` §Access Permissions.
   * - ``pdHandler``
     - 32
     - PD handler from the PD allocation response.
   * - ``lkeyOrNot``
     - 1
     - ``1`` = also allocate an lkey (always ``1`` in practice).
   * - ``lkeyPart``
     - ``MR_LKEYPART_B``
     - Partial lkey (upper bits).  Pass ``0``; FPGA assigns.
   * - ``rkeyPart``
     - ``MR_RKEYPART_B``
     - Partial rkey (upper bits).  Pass the host ``ibv_mr.rkey``
       right-shifted by ``MR_INDEX_B`` bits to strip the slot index.
   * - ``busType``
     - 2
     - ``1`` (MR).  Always at bits [302:301].

MR Response (RX bus)
---------------------

The response fields are packed from bit 0 as follows (derived from the
``respMr`` class):

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Field
     - Bit range
     - Description
   * - ``rKey``
     - ``[MR_KEY_B−1 : 0]``
     - Full remote key assigned to this MR.
   * - ``lKey``
     - ``[2·MR_KEY_B−1 : MR_KEY_B]``
     - Full local key assigned to this MR.
   * - ``mrRKeyPart``
     - ``[2·MR_KEY_B + MR_RKEYPART_B−1 : 2·MR_KEY_B]``
     - Partial rkey (upper bits).
   * - ``mrLKeyPart``
     - next ``MR_LKEYPART_B`` bits
     - Partial lkey (upper bits).
   * - ``mrPdHandler``
     - next 32 bits
     - PD handler associated with this MR.
   * - ``mrAccFlags``
     - next 8 bits
     - Access flags echoed from the request.
   * - ``mrLen``
     - next 32 bits
     - Length echoed from the request.
   * - ``mrLAddr``
     - next 64 bits
     - Local address echoed from the request.
   * - ``successOrNot``
     - next 1 bit
     - ``1`` = success.
   * - ``busType``
     - ``[275:274]``
     - ``1`` — echoes the MR request type.

The fields most commonly used by the host are ``lKey`` (to be written into
the WorkReqDispatcher ``lKey`` register) and ``successOrNot``.

rkey vs rkeyPart
~~~~~~~~~~~~~~~~~

The host ``ibv_mr.rkey`` is a 32-bit value.  The FPGA's MR resource manager
uses the lowest ``MR_INDEX_B`` bits as a slot index.  When sending the MR
allocation request, supply ``rkeyPart = rkey >> MR_INDEX_B`` (the upper
``MR_RKEYPART_B`` bits).  The FPGA reassembles the full rkey by appending
the slot index.

MR Length and Slot Layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``len`` field should be set to the full slab size::

    len = rxQueueDepth × maxPayload

This covers the entire pre-registered MR slab and allows the FPGA to write
into any slot offset within it.
