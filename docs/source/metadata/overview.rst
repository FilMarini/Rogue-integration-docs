Metadata Channel Overview
=========================

The **Metadata Channel** is the control plane used to configure the FPGA's
internal RDMA resource manager.  It is implemented as a pair of wide AXI-lite
registers in the RoCEv2 engine register block:

.. list-table::
   :header-rows: 1
   :widths: 15 15 15 55

   * - Offset
     - Bits
     - Name
     - Description
   * - ``0xF00`` [0]
     - 1
     - ``SendMetaData``
     - Control bit.  Write ``0→1→0`` to trigger a metadata transaction.
       The rising edge starts the FPGA state machine.
   * - ``0xF00`` [1]
     - 1
     - ``RecvMetaData``
     - Status bit.  Reads ``1`` when the FPGA has placed a response in
       ``MetaDataRx``.  Cleared automatically when the next transaction
       is triggered.
   * - ``0xF04``
     - 303
     - ``MetaDataTx``
     - Request bus.  Write before asserting ``SendMetaData``.
       Spans offsets ``0xF04``–``0xF28`` (10 × 32-bit words, last word
       uses only 15 bits).
   * - ``0xF2C``
     - 276
     - ``MetaDataRx``
     - Response bus.  Read after ``RecvMetaData`` goes high.
       Spans offsets ``0xF2C``–``0xF4C`` (9 × 32-bit words, last word
       uses only 20 bits).

.. note::
   The ``SendMetaData`` and ``RecvMetaData`` bits share register address
   ``0xF00``.  They occupy separate bit positions (0 and 1 respectively) and
   can be read/written independently using pyrogue ``bitOffset``.

Transaction Protocol
---------------------

Each metadata transaction is a **request–response** exchange:

1. **Write** the 303-bit request value into ``MetaDataTx``.
2. **Pulse** ``SendMetaData``: write ``0``, then ``1``, then ``0``.
   The rising edge (``0→1``) triggers the FPGA state machine.
3. **Poll** ``RecvMetaData`` until it reads ``1`` (the FPGA has
   processed the request and written the response).
4. **Read** ``MetaDataRx`` (276 bits) to get the response.

.. important::
   The FPGA triggers on the **rising edge** of ``SendMetaData``.  If the bit
   is already ``1`` from a previous write, a subsequent write of ``1`` will
   have no effect.  Always write ``0`` first to guarantee a clean edge.

   The recommended Python helper follows this sequence::

       engine.SendMetaData.set(0)
       engine.MetaDataTx.set(request_value)
       engine.SendMetaData.set(1)
       engine.SendMetaData.set(0)

       # Poll with timeout
       deadline = time.monotonic() + TIMEOUT_S
       while not engine.RecvMetaData.get():
           if time.monotonic() > deadline:
               raise TimeoutError("MetaData response timeout")
           time.sleep(0.001)

       response = engine.MetaDataRx.get()

Field Encoding Convention
--------------------------

Both TX and RX buses use **LSB-first** packing.  Fields are placed starting
from **bit 0**, with each successive field immediately above the previous one.
The two most-significant bits of each bus carry the ``busType`` tag:

* TX bus (303 bits): ``busType`` at bits **[302:301]**
* RX bus (276 bits): ``busType`` at bits **[275:274]**

All other fields are packed from bit 0 upward in the order listed in the
message definitions.  There is no padding between fields; the space between
the top of the payload fields and the ``busType`` bits is unused/zero.

Bus Type Field
--------------

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - Value
     - Name
     - Description
   * - ``0``
     - PD
     - Protection Domain request/response
   * - ``1``
     - MR
     - Memory Region request/response
   * - ``2``
     - QP
     - Queue Pair request/response

Message Types
-------------

.. toctree::
   :maxdepth: 1

   pd_messages
   mr_messages
   qp_messages
   response_decoding
