RoceEngine (Python)
===================

``pyrogue.protocols.RoceEngine`` is a :class:`pyrogue.Device` that maps the
FPGA RoCEv2 engine's AXI-lite register block and provides helper methods for
driving the metadata bus.

Class Reference
---------------

.. code-block:: python

    class pyrogue.protocols.RoceEngine(pr.Device):

Constructor Parameters
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter
     - Type
     - Description
   * - ``name``
     - str
     - pyrogue device name
   * - ``memBase``
     - object
     - Memory bus master (SRP interface or similar)
   * - ``offset``
     - int
     - Base address of the RoCEv2 engine in the FPGA address space
   * - ``**kwargs``
     - Any
     - Forwarded to :class:`pyrogue.Device`

Raw Register Variables
~~~~~~~~~~~~~~~~~~~~~~

These variables provide direct access to the AXI-lite registers.  They
are hidden from the default pyrogue GUI but accessible programmatically.

.. list-table::
   :header-rows: 1
   :widths: 20 12 12 12 44

   * - Name
     - Offset
     - BitSize
     - Mode
     - Description
   * - ``SendMetaData``
     - ``0xF00`` [0]
     - 1
     - RW
     - Pulse ``0→1→0`` to trigger a metadata transaction.
   * - ``RecvMetaData``
     - ``0xF00`` [1]
     - 1
     - RO
     - ``1`` when a response is ready in ``MetaDataRx``.
   * - ``MetaDataTx``
     - ``0xF04``
     - 303
     - RW
     - 303-bit TX bus.  Write before asserting ``SendMetaData``.
   * - ``MetaDataRx``
     - ``0xF2C``
     - 276
     - RO
     - 276-bit RX bus.  Read after ``RecvMetaData`` goes high.

DCQCN Register Variables
~~~~~~~~~~~~~~~~~~~~~~~~~

See :doc:`../dcqcn/registers` for full descriptions.

.. list-table::
   :header-rows: 1
   :widths: 25 12 12 51

   * - Name
     - Offset
     - BitSize
     - Description
   * - ``DcqcnRateIncInt``
     - ``0x000``
     - 32
     - Rate increase interval (clock cycles)
   * - ``DcqcnRateDecInt``
     - ``0x004``
     - 32
     - Rate decrease interval (clock cycles)
   * - ``DcqcnAlphaUpdateInt``
     - ``0x008``
     - 32
     - Alpha decay interval (clock cycles)
   * - ``DcqcnAlphaG``
     - ``0x00C``
     - 10
     - Alpha EWMA weight (10-bit fixed-point)
   * - ``DcqcnClampTgtRate``
     - ``0x010``
     - 1
     - Clamp target rate on CNP
   * - ``DcqcnRai``
     - ``0x014``
     - 32
     - Additive increase step (bytes/sec)
   * - ``DcqcnRhai``
     - ``0x018``
     - 32
     - Hyper-active increase step (bytes/sec)

Internal Methods
~~~~~~~~~~~~~~~~

These methods are called by ``RoCEv2Server._start()`` and are not intended
for direct use in application code.

``_setup_connection(server) → None``
    Runs the full six-step metadata bus handshake:
    PD alloc → MR alloc → QP create → INIT → RTR → RTS.
    See :doc:`../integration/connection_flow` for the full sequence.

``_send_meta(tx_value: int) → int``
    Low-level: write ``tx_value`` to ``MetaDataTx``, pulse
    ``SendMetaData``, wait for ``RecvMetaData``, return ``MetaDataRx``.

``_encode_alloc_pd() → int``
``_encode_alloc_mr(laddr, length, acc_flags, pd_handler, rkey) → int``
``_encode_create_qp(pd_handler, qp_type) → int``
``_encode_modify_qp_init(qpn, pd_handler) → int``
``_encode_modify_qp_rtr(qpn, pd_handler, host_qpn, host_gid, rq_psn, path_mtu) → int``
``_encode_modify_qp_rts(qpn, pd_handler, sq_psn, timeout, retry_cnt, rnr_retry) → int``
    Field encoders for each metadata bus message type.
    See :doc:`../metadata/pd_messages`, :doc:`../metadata/mr_messages`,
    :doc:`../metadata/qp_messages` for the bit layouts.
