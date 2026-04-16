MR Messages (Memory Region)
============================

Memory Region messages register or deregister a memory region in the FPGA's
internal resource manager.  The bus type tag for MR messages is ``0b01``
(value ``1``).

An MR represents the host memory buffer that the FPGA will write into via
RDMA.  The MR carries the host virtual address (``laddr``), length, remote
key (``rkey``), and access permissions.

MR Request (TX bus)
--------------------

Payload fields (packed MSB-first in order listed):

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Field
     - Width (bits)
     - Description
   * - ``allocOrNot``
     - 1
     - ``1`` = register (allocate), ``0`` = deregister (free)
   * - ``laddr``
     - 64
     - Host virtual address of the memory region (the ``addr`` field of
       ``ibv_mr`` returned by ``ibv_reg_mr()``)
   * - ``len``
     - 32
     - Length of the memory region in bytes
   * - ``accFlags``
     - 8
     - Access permissions (see :doc:`bus_layout` §Access Permissions).
       Use ``0x0F`` for the FPGA-target MR.
   * - ``pdHandler``
     - 32
     - PD handler returned by the PD allocation response
   * - ``lkeyOrNot``
     - 1
     - ``1`` = also allocate an lkey (always ``1`` in practice)
   * - ``lkeyPart``
     - 28
     - Partial lkey (``MR_KEY_B − MR_INDEX_B``).  Pass ``0``; FPGA
       assigns.
   * - ``rkeyPart``
     - 28
     - Partial rkey.  Pass the ``rkey`` from the host ``ibv_mr``,
       right-shifted by ``MR_INDEX_B`` (4 bits) to strip the index
       portion.

Total payload width::

    1 + 64 + 32 + 8 + 32 + 1 + 28 + 28 = 194 bits

Padding::

    303 − 2 − 194 = 107 bits (zero, between busType and first payload field)

Full TX bus layout:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 40

   * - Bits [302:0]
     - Field
     - Width
     - Notes
   * - ``[302:301]``
     - ``busType``
     - 2
     - ``0b01``
   * - ``[300:194]``
     - padding
     - 107
     - zeros
   * - ``[193]``
     - ``allocOrNot``
     - 1
     -
   * - ``[192:129]``
     - ``laddr``
     - 64
     - Host virtual address (little-endian on x86; passed as-is)
   * - ``[128:97]``
     - ``len``
     - 32
     - Byte length
   * - ``[96:89]``
     - ``accFlags``
     - 8
     -
   * - ``[88:57]``
     - ``pdHandler``
     - 32
     -
   * - ``[56]``
     - ``lkeyOrNot``
     - 1
     -
   * - ``[55:28]``
     - ``lkeyPart``
     - 28
     -
   * - ``[27:0]``
     - ``rkeyPart``
     - 28
     -

Python Encoder
~~~~~~~~~~~~~~

.. code-block:: python

    BUS_TYPE_MR = 0b01

    def encode_alloc_mr(
        laddr:      int,
        length:     int,
        acc_flags:  int,
        pd_handler: int,
        rkey:       int,
        lkey_part:  int = 0,
        lkey_or_not: int = 1,
    ) -> int:
        """Encode an MR allocation request."""
        rkey_part = (rkey >> 4) & 0x0FFFFFFF   # strip 4-bit MR_INDEX
        return (
            (BUS_TYPE_MR  << 301) |
            (1            << 193) |   # allocOrNot
            (laddr        << 129) |
            (length       << 97)  |
            (acc_flags    << 89)  |
            (pd_handler   << 57)  |
            (lkey_or_not  << 56)  |
            (lkey_part    << 28)  |
            rkey_part
        )

MR Response (RX bus)
---------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 40

   * - Bits [275:0]
     - Field
     - Width
     - Description
   * - ``[275:274]``
     - ``busType``
     - 2
     - ``0b01``
   * - ``[273]``
     - ``successOrNot``
     - 1
     - ``1`` = success
   * - ``[272:241]``
     - ``lkey``
     - 32
     - The local key assigned to this MR by the FPGA.  Used by the
       FPGA engine to validate its own WRITE operations against
       this MR.
   * - ``[240:0]``
     - padding
     - 241
     - zeros

Python Decoder
~~~~~~~~~~~~~~

.. code-block:: python

    def decode_mr_resp(rx: int) -> tuple[bool, int]:
        """Return (success, lkey)."""
        success = bool((rx >> (META_DATA_RX_BITS - 3)) & 1)
        lkey    = (rx >> (META_DATA_RX_BITS - 3 - 32)) & 0xFFFFFFFF
        return success, lkey

Important Notes
---------------

rkey vs rkeyPart
~~~~~~~~~~~~~~~~~

The host ``ibv_mr.rkey`` is a 32-bit value.  The FPGA's MR resource manager
uses the lowest ``MR_INDEX_B = 4`` bits of the key as a slot index.  When
sending the MR allocation request, supply ``rkeyPart = rkey >> 4`` (the upper
28 bits).  The FPGA reassembles the full rkey internally by appending the
slot index.

Because the host and FPGA agree on the rkey value, the FPGA will use
``rkey`` (as registered with the host NIC) in its RDMA WRITE work requests,
which the host NIC validates against the registered MR.

MR Length and Slot Layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``len`` field should be set to the full slab size::

    len = rxQueueDepth × maxPayload

This covers the entire pre-registered MR slab and allows the FPGA to write
into any slot offset within it.
