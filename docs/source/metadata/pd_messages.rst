PD Messages (Protection Domain)
================================

Protection Domain messages allocate or free a PD in the FPGA's internal
resource manager.  The bus type tag for PD messages is ``0`` (``METADATA_PD_T``).

Fields are packed **LSB-first**: bit 0 holds the first field, with each
successive field placed immediately above.  The ``busType`` tag sits at the
two MSBs of the bus ([302:301] for TX, [275:274] for RX).

PD Request (TX bus)
--------------------

Fields packed from bit 0:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Width (bits)
     - Description
   * - ``allocOrNot``
     - 1
     - ``1`` = allocate, ``0`` = free.  Occupies bit [0].
   * - ``pdKey``
     - ``PD_KEY_B``
     - Key portion of the PD handler.  For allocation, pass ``0``.
       For free, supply the key portion of the handler returned during
       allocation.
   * - ``pdHandler``
     - 32
     - Full PD handler.  For allocation pass ``0``; for free pass the
       handler returned at allocation time.
   * - ``busType``
     - 2
     - ``0`` (PD).  Always at bits [302:301].

PD Response (RX bus)
---------------------

Fields packed from bit 0, decoded as:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Bits
     - Description
   * - ``pdKey``
     - ``[PD_KEY_B−1 : 0]``
     - Key portion of the allocated PD handler.
   * - ``pdHandler``
     - ``[PD_KEY_B+31 : PD_KEY_B]``
     - Full 32-bit PD handler.  Pass this verbatim to all subsequent
       MR and QP create requests.
   * - ``successOrNot``
     - ``[PD_KEY_B+32]``
     - ``1`` = operation succeeded, ``0`` = failure.
   * - ``busType``
     - ``[275:274]``
     - ``0`` — echoes the PD request type.

Python decoder::

    pd_key_b    = PD_KEY_B          # = PD_HANDLER_B - PD_INDEX_B
    pdKey       = rx & ((1 << pd_key_b) - 1)
    pdHandler   = (rx >> pd_key_b) & 0xFFFFFFFF
    successOrNot = (rx >> (pd_key_b + 32)) & 1
    busType     = (rx >> 274) & 0x3

PD Handler Layout
------------------

The 32-bit ``pdHandler`` returned by the FPGA encodes the PD index and key::

    Bits [31 : PD_INDEX_B]  — pdKey   (PD_KEY_B bits)
    Bits [PD_INDEX_B-1 : 0] — pdIndex (PD_INDEX_B bits)

The host stores the full 32-bit handler and passes it back verbatim to the
FPGA in MR and QP create requests.
