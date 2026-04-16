PD Messages (Protection Domain)
================================

Protection Domain messages allocate or free a PD in the FPGA's internal
resource manager.  The bus type tag for PD messages is ``0b00`` (value ``0``).

PD Request (TX bus)
--------------------

Payload width: ``PD_ALLOC_OR_NOT_B + PD_KEY_B + PD_HANDLER_B = 62 bits``

The 62-bit payload is placed at the **least-significant** end of the 303-bit
bus, immediately below the padding:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 40

   * - Bits [302:0]
     - Field
     - Width (bits)
     - Description
   * - ``[302:301]``
     - ``busType``
     - 2
     - Must be ``0b00`` for PD messages
   * - ``[300:242]``
     - padding
     - 59
     - Zero-filled.  (303 − 2 − 62 − 1 = 239 total padding bits below
       bus type, of which 59 are before the payload start and the
       remaining zeros are embedded in the handler field for alloc.)
   * - ``[241]``
     - ``allocOrNot``
     - 1
     - ``1`` = allocate, ``0`` = free
   * - ``[240:212]``
     - ``pdKey``
     - 29
     - Key portion of the PD handler.  For allocation requests, pass
       ``0``; the FPGA assigns the key and returns it in the response.
       For free requests, supply the ``pdKey`` portion of the handler.
   * - ``[211:180]``
     - ``pdHandler``
     - 32
     - Full PD handler.  For allocation requests this is
       typically ``0`` (FPGA fills it in).  For free requests,
       supply the handler returned during allocation.
   * - ``[179:0]``
     - unused
     - 180
     - Structural zeros — these positions are covered by the padding
       field above.  The padding total is
       ``303 − 2 − 62 = 239`` bits.

.. note::
   The exact padding calculation::

       meta_len = PD_ALLOC_OR_NOT_B + PD_KEY_B + PD_HANDLER_B
                = 1 + 29 + 32 = 62 bits
       padding  = META_DATA_BITS − meta_len = 303 − 62 = 241 bits

   After the 2-bit ``busType`` field, there are 239 padding bits before
   the first payload field (``allocOrNot``).  In Python::

       bus = (BUS_TYPE_PD << 301) | (alloc_or_not << 241) | \
             (pd_key << 212)      | pd_handler

Python Encoder
~~~~~~~~~~~~~~

.. code-block:: python

    BUS_TYPE_PD = 0b00
    META_DATA_BITS = 303

    def encode_alloc_pd(pd_key: int = 0, pd_handler: int = 0) -> int:
        """Encode a PD allocation request (allocOrNot=1)."""
        return (BUS_TYPE_PD     << 301) | \
               (1               << 241) | \
               (pd_key          << 212) | \
               pd_handler

    def encode_free_pd(pd_handler: int) -> int:
        """Encode a PD free request (allocOrNot=0)."""
        pd_key = (pd_handler >> 3) & 0x1FFFFFFF  # strip 3-bit index
        return (BUS_TYPE_PD     << 301) | \
               (0               << 241) | \
               (pd_key          << 212) | \
               pd_handler

PD Response (RX bus)
---------------------

Response width: ``successOrNot(1) + pdHandler(32) = 33 bits`` below bus type.

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 40

   * - Bits [275:0]
     - Field
     - Width (bits)
     - Description
   * - ``[275:274]``
     - ``busType``
     - 2
     - ``0b00`` — echoes PD request
   * - ``[273]``
     - ``successOrNot``
     - 1
     - ``1`` = operation succeeded
   * - ``[272:241]``
     - ``pdHandler``
     - 32
     - The allocated PD handler.  Use this value in all subsequent MR
       and QP requests that reference this PD.
   * - ``[240:0]``
     - padding
     - 241
     - Zero

Python Decoder
~~~~~~~~~~~~~~

.. code-block:: python

    META_DATA_RX_BITS = 276

    def decode_pd_resp(rx: int) -> tuple[bool, int]:
        """Return (success, pd_handler) from a PD response bus."""
        success    = bool((rx >> (META_DATA_RX_BITS - 3)) & 1)
        pd_handler = (rx >> (META_DATA_RX_BITS - 3 - 32)) & 0xFFFFFFFF
        return success, pd_handler

PD Handler Layout
------------------

The 32-bit ``pdHandler`` returned by the FPGA encodes both the PD index and
a key::

    Bits [31:3]  — pdKey    (29 bits)
    Bits [ 2:0]  — pdIndex  (3 bits, log₂(MAX_PD=8))

The host stores the full 32-bit handler and passes it back verbatim to the
FPGA in MR and QP create requests.  The split into ``pdKey``/``pdIndex`` is
an implementation detail of the FPGA resource manager and is not normally
needed by host software.
