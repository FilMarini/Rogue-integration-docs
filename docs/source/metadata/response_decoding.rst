Response Decoding
=================

All metadata responses share the same 276-bit RX bus format.  This page
provides a unified reference for decoding responses and handling errors.

Common Header
-------------

Every response, regardless of type, has the same 3-bit header at the top of
the 276-bit bus:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Bits [275:0]
     - Field
     - Description
   * - ``[275:274]``
     - ``busType``
     - Echoes the TX bus type (0=PD, 1=MR, 2=QP)
   * - ``[273]``
     - ``successOrNot``
     - ``1`` = operation succeeded, ``0`` = failure

Reading the Bus Type
--------------------

.. code-block:: python

    META_DATA_RX_BITS = 276

    def rx_bus_type(rx: int) -> int:
        return (rx >> (META_DATA_RX_BITS - 2)) & 0x3

    def rx_success(rx: int) -> bool:
        return bool((rx >> (META_DATA_RX_BITS - 3)) & 1)

Dispatch by Bus Type
--------------------

.. code-block:: python

    BUS_TYPE_PD = 0
    BUS_TYPE_MR = 1
    BUS_TYPE_QP = 2

    def decode_response(rx: int):
        bt = rx_bus_type(rx)
        if not rx_success(rx):
            raise RoceMetaDataError(f"FPGA returned failure for bus_type={bt}")

        if bt == BUS_TYPE_PD:
            return decode_pd_resp(rx)
        elif bt == BUS_TYPE_MR:
            return decode_mr_resp(rx)
        elif bt == BUS_TYPE_QP:
            return decode_qp_resp(rx)
        else:
            raise RoceMetaDataError(f"Unknown bus_type={bt} in response")

Failure Codes
-------------

When ``successOrNot = 0``, the FPGA does not populate the payload fields.
The following conditions cause the FPGA to return a failure:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Message
     - Failure conditions
   * - PD alloc
     - No free PD slots (``MAX_PD`` already allocated)
   * - PD free
     - Invalid ``pdHandler`` (handler not in use)
   * - MR alloc
     - No free MR slots for the given PD; invalid ``pdHandler``
   * - MR free
     - Invalid MR/PD combination
   * - QP create
     - Internal resource exhaustion
   * - QP modify
     - Invalid QP number; invalid state transition; attribute mask
       includes unsupported attributes

Polling Best Practices
----------------------

Always implement a **timeout** when waiting for ``RecvMetaData``:

.. code-block:: python

    import time

    METADATA_TIMEOUT_S = 2.0   # generous for FPGA processing

    def wait_for_response(engine) -> int:
        deadline = time.monotonic() + METADATA_TIMEOUT_S
        while True:
            if engine.RecvMetaData.get():
                return engine.MetaDataRx.get()
            if time.monotonic() > deadline:
                raise TimeoutError(
                    "Timed out waiting for MetaDataRx response"
                )
            time.sleep(0.001)

And always pulse ``SendMetaData`` as ``0 → 1 → 0`` to guarantee a clean
rising edge, even at the start of a session:

.. code-block:: python

    def send_metadata(engine, tx_value: int) -> int:
        engine.SendMetaData.set(0)        # ensure starting from 0
        engine.MetaDataTx.set(tx_value)
        engine.SendMetaData.set(1)        # rising edge triggers FPGA
        engine.SendMetaData.set(0)        # clean up
        return wait_for_response(engine)

Complete Handshake Reference
-----------------------------

For a summary of the full six-step handshake with expected
request/response pairs, see :doc:`../integration/connection_flow`.
