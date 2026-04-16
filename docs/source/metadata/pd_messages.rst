PD Messages (Protection Domain)
================================

Protection Domain messages allocate or free a PD.
Bus type tag: ``0`` (``METADATA_PD_T``).

Fields are packed **LSB-first** from bit 0.  ``busType`` is fixed at the
two MSBs of the bus.

.. note::
   With ``MAX_PD = 1``, ``PD_INDEX_B = 0`` and ``PD_KEY_B = 32``
   (equal to ``PD_HANDLER_B``).

PD Request (TX, 303-bit bus)
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
     - ``1`` = allocate, ``0`` = free.
   * - ``pdKey``
     - ``[32:1]``
     - 32
     - Key portion of the PD handler.  Pass ``0`` for allocation;
       supply the key from the handler for free.
   * - ``pdHandler``
     - ``[64:33]``
     - 32
     - Full PD handler.  Pass ``0`` for allocation; supply the
       handler from the allocation response for free.
   * - ``busType``
     - ``[302:301]``
     - 2
     - ``0`` (PD).  Fixed at the two MSBs.

PD Response (RX, 276-bit bus)
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Field
     - Bits
     - Width
     - Description
   * - ``pdKey``
     - ``[31:0]``
     - 32
     - Key portion of the allocated PD handler.
   * - ``pdHandler``
     - ``[63:32]``
     - 32
     - Full 32-bit PD handler.  Pass this verbatim to all subsequent
       MR and QP create requests.
   * - ``successOrNot``
     - ``[64]``
     - 1
     - ``1`` = success, ``0`` = failure.
   * - ``busType``
     - ``[275:274]``
     - 2
     - ``0`` — echoes the PD request type.  Fixed at the two MSBs.

Python decoder:

.. code-block:: python

    pdKey        = rx & 0xFFFFFFFF
    pdHandler    = (rx >> 32) & 0xFFFFFFFF
    successOrNot = (rx >> 64) & 1
    busType      = (rx >> 274) & 0x3
