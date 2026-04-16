Metadata Bus (internal to RoCEv2Server)
========================================

The metadata bus logic is integrated directly into
``pyrogue.protocols.RoCEv2Server`` — there is no separate ``RoceEngine``
pyrogue device.

The AXI-lite registers that the Python layer accesses via SRP/UDP are:

.. list-table::
   :header-rows: 1
   :widths: 14 14 10 62

   * - Offset
     - BitSize
     - Mode
     - Description
   * - ``0xF00`` [0]
     - 1
     - RW
     - ``SendMetaData`` — pulse ``0→1→0`` to trigger a transaction.
   * - ``0xF00`` [1]
     - 1
     - RO
     - ``RecvMetaData`` — ``1`` when a response is ready.
   * - ``0xF04``
     - 303
     - RW
     - ``MetaDataTx`` — 303-bit request bus.
   * - ``0xF2C``
     - 276
     - RO
     - ``MetaDataRx`` — 276-bit response bus.

These are accessed as ``RemoteVariable`` entries mapped on the SRP memory
bus at the RoCEv2 engine base offset.  All encoding/decoding is done
inside ``RoCEv2Server._start()`` and ``_stop()``.

For the full bit-level documentation of what is written to these registers,
see :doc:`../metadata/overview` and the message-type pages linked from it.
