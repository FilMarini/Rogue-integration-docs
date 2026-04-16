Response Decoding
=================

All metadata responses share the same 276-bit RX bus format.  The
``busType`` tag is always at bits **[275:274]**.  All payload fields are
packed **LSB-first** from bit 0.

Reading the Bus Type
--------------------

.. code-block:: python

    busType = (rx >> 274) & 0x3   # always at [275:274]

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
        pdKey        = rx & 0xFFFFFFFF          # [31:0]
        pdHandler    = (rx >> 32) & 0xFFFFFFFF  # [63:32]
        successOrNot = (rx >> 64) & 1           # [64]
        return successOrNot, pdHandler

    def decode_mr_resp(rx: int):
        rKey         = rx & 0xFFFFFFFF                      # [31:0]
        lKey         = (rx >> 32) & 0xFFFFFFFF              # [63:32]
        successOrNot = (rx >> 256) & 1                      # [256]
        return successOrNot, lKey, rKey

    def decode_qp_resp(rx: int):
        qpn          = (rx >> 249) & 0xFFFFFF   # [272:249]
        successOrNot = (rx >> 273) & 1           # [273]
        qpaQpState   = (rx >> 213) & 0xF         # [216:213]
        pdHandler    = (rx >> 217) & 0xFFFFFFFF  # [248:217]
        return successOrNot, qpn, qpaQpState, pdHandler

``successOrNot`` Position Summary
----------------------------------

The ``successOrNot`` bit sits at a different absolute position depending on
message type, because it immediately follows the payload fields:

.. list-table::
   :header-rows: 1
   :widths: 15 15 70

   * - Type
     - Bit
     - Reason
   * - PD
     - ``[64]``
     - After ``pdKey[31:0]`` + ``pdHandler[63:32]``
   * - MR
     - ``[256]``
     - After all MR payload fields (rKey+lKey+parts+handler+flags+len+addr)
   * - QP
     - ``[273]``
     - Fixed, immediately below ``busType[275:274]``

Failure Cases
-------------

When ``successOrNot = 0``:

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Message
     - Common failure conditions
   * - PD alloc
     - ``MAX_PD = 1`` already allocated — previous session was not torn
       down cleanly.  Reset the FPGA firmware.
   * - MR alloc
     - Invalid ``pdHandler``, or no free MR slots.
   * - QP create
     - Internal resource exhaustion.
   * - QP modify
     - Invalid QP number; invalid state transition; unsupported mask.

Polling Best Practices
----------------------

Always use the ``0→1→0`` pulse and include a timeout:

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
