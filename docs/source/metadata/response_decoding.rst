Response Decoding
=================

All metadata responses share the same 276-bit RX bus format.  The
``busType`` tag always sits at bits **[275:274]**; all payload fields are
packed **LSB-first** from bit 0.

Reading the Bus Type and Success Flag
--------------------------------------

The ``busType`` and ``successOrNot`` positions are fixed across all
response types:

.. code-block:: python

    busType     = (rx >> 274) & 0x3
    # successOrNot position depends on message type:
    #   PD:  bit  PD_KEY_B + PD_HANDLER_B
    #   MR:  bit  (sum of all MR payload fields)
    #   QP:  bit  273

The QP response is the special case where ``successOrNot`` is always at
bit 273 (immediately below ``busType``).

Dispatch by Bus Type
--------------------

.. code-block:: python

    METADATA_PD_T = 0
    METADATA_MR_T = 1
    METADATA_QP_T = 2

    def decode_response(rx: int):
        bt = (rx >> 274) & 0x3

        if bt == METADATA_PD_T:
            return decode_pd_resp(rx)
        elif bt == METADATA_MR_T:
            return decode_mr_resp(rx)
        elif bt == METADATA_QP_T:
            return decode_qp_resp(rx)
        else:
            raise RoceMetaDataError(f"Unknown busType={bt}")

    def decode_pd_resp(rx: int):
        pdKey        = rx & ((1 << PD_KEY_B) - 1)
        pdHandler    = (rx >> PD_KEY_B) & 0xFFFFFFFF
        successOrNot = (rx >> (PD_KEY_B + PD_HANDLER_B)) & 1
        return successOrNot, pdHandler

    def decode_mr_resp(rx: int):
        rKey         = rx & 0xFFFFFFFF
        lKey         = (rx >> MR_KEY_B) & 0xFFFFFFFF
        # successOrNot is above all the MR payload fields
        offset       = MR_KEY_B + MR_KEY_B + MR_RKEYPART_B + \
                       MR_LKEYPART_B + MR_PDHANDLER_B + \
                       MR_ACCFLAGS_B + MR_LEN_B + MR_LADDR_B
        successOrNot = (rx >> offset) & 1
        return successOrNot, lKey, rKey

    def decode_qp_resp(rx: int):
        qpn          = (rx >> 249) & 0xFFFFFF
        successOrNot = (rx >> 273) & 1
        qp_state     = (rx >> 213) & 0xF   # qpaQpState
        return successOrNot, qpn, qp_state

Failure Cases
-------------

When ``successOrNot = 0``, the FPGA does not populate the payload fields.
Common causes:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Message
     - Failure conditions
   * - PD alloc
     - No free PD slots (``MAX_PD = 1`` already allocated — previous
       session was not torn down cleanly)
   * - MR alloc
     - Invalid ``pdHandler``, or no free MR slots
   * - QP create
     - Internal resource exhaustion
   * - QP modify
     - Invalid QP number; invalid state transition; unsupported
       attribute mask

Polling Best Practices
----------------------

Always implement a **timeout** when waiting for ``RecvMetaData``:

.. code-block:: python

    import time

    METADATA_TIMEOUT_S = 2.0

    def send_metadata(engine, tx_value: int) -> int:
        engine.SendMetaData.set(0)
        engine.MetaDataTx.set(tx_value)
        engine.SendMetaData.set(1)
        engine.SendMetaData.set(0)

        deadline = time.monotonic() + METADATA_TIMEOUT_S
        while True:
            if engine.RecvMetaData.get():
                return engine.MetaDataRx.get()
            if time.monotonic() > deadline:
                raise TimeoutError("Timed out waiting for MetaDataRx")
            time.sleep(0.001)
