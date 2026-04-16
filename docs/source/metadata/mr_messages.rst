MR Messages (Memory Region)
============================

Memory Region messages register or deregister a memory region.
Bus type tag: ``1`` (``METADATA_MR_T``).

Fields are packed **LSB-first** from bit 0.  ``busType`` is fixed at the
two MSBs of the bus.

.. note::
   With ``MAX_MR = 16`` and ``MAX_PD = 1``:
   ``MR_INDEX_B = 4``, ``MR_LKEYPART_B = MR_RKEYPART_B = 28``.

MR Request (TX, 303-bit bus)
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Field
     - Bits
     - Width
     - Description
   * - ``allocOrNot``
     - ``[0:0]``
     - 1
     - ``1`` = register (allocate), ``0`` = deregister (free).
   * - ``laddr``
     - ``[64:1]``
     - 64
     - Host virtual address of the memory region (``ibv_mr.addr``).
   * - ``len``
     - ``[96:65]``
     - 32
     - Byte length of the memory region.
   * - ``accFlags``
     - ``[104:97]``
     - 8
     - Access permissions.  Use ``0x0F`` for the FPGA-target MR.
       See :doc:`bus_layout` §Access Permissions.
   * - ``pdHandler``
     - ``[136:105]``
     - 32
     - PD handler from the PD allocation response.
   * - ``lkeyOrNot``
     - ``[137:137]``
     - 1
     - ``1`` = also allocate an lkey (always ``1`` in practice).
   * - ``lkeyPart``
     - ``[165:138]``
     - 28
     - Partial lkey upper bits.  Pass ``0``; FPGA assigns.
   * - ``rkeyPart``
     - ``[193:166]``
     - 28
     - Partial rkey upper bits.  Pass ``host_rkey >> 4`` (strip the
       4-bit ``MR_INDEX_B`` slot index from the host ``ibv_mr.rkey``).
   * - ``busType``
     - ``[302:301]``
     - 2
     - ``1`` (MR).  Fixed at the two MSBs.

MR Response (RX, 276-bit bus)
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Field
     - Bits
     - Width
     - Description
   * - ``rKey``
     - ``[31:0]``
     - 32
     - Full remote key assigned to this MR by the FPGA.
   * - ``lKey``
     - ``[63:32]``
     - 32
     - Full local key assigned to this MR by the FPGA.  Write this
       to the WorkReqDispatcher ``lKey`` register.
   * - ``mrRKeyPart``
     - ``[91:64]``
     - 28
     - Partial rkey (upper 28 bits, without the 4-bit slot index).
   * - ``mrLKeyPart``
     - ``[119:92]``
     - 28
     - Partial lkey (upper 28 bits).
   * - ``mrPdHandler``
     - ``[151:120]``
     - 32
     - PD handler associated with this MR (echoed from request).
   * - ``mrAccFlags``
     - ``[159:152]``
     - 8
     - Access flags (echoed from request).
   * - ``mrLen``
     - ``[191:160]``
     - 32
     - Length (echoed from request).
   * - ``mrLAddr``
     - ``[255:192]``
     - 64
     - Local address (echoed from request).
   * - ``successOrNot``
     - ``[256]``
     - 1
     - ``1`` = success, ``0`` = failure.
   * - ``busType``
     - ``[275:274]``
     - 2
     - ``1`` — echoes the MR request type.  Fixed at the two MSBs.

Python decoder:

.. code-block:: python

    rKey         = rx & 0xFFFFFFFF
    lKey         = (rx >> 32) & 0xFFFFFFFF
    mrRKeyPart   = (rx >> 64) & 0x0FFFFFFF
    mrLKeyPart   = (rx >> 92) & 0x0FFFFFFF
    mrPdHandler  = (rx >> 120) & 0xFFFFFFFF
    mrAccFlags   = (rx >> 152) & 0xFF
    mrLen        = (rx >> 160) & 0xFFFFFFFF
    mrLAddr      = (rx >> 192) & 0xFFFFFFFFFFFFFFFF
    successOrNot = (rx >> 256) & 1
    busType      = (rx >> 274) & 0x3
