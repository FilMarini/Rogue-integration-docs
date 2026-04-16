C++ Server (rogue.protocols.rocev2)
====================================

The C++ layer provides the low-level RDMA plumbing via ``libibverbs``.

Python-Accessible Interface
----------------------------

The C++ ``Server`` class exposes the following methods to Python via
Boost.Python bindings:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Method
     - Description
   * - ``Server(rdmaDevice, rxQueueDepth, maxPayload)``
     - Constructor.  Opens the RDMA device, allocates PD, registers MR,
       creates RC QP and transitions to INIT.
   * - ``getQpNum() → int``
     - Returns the host QP number (24-bit).  Available after construction.
   * - ``getGid() → str``
     - Returns the host GID as a colon-separated hex string.
   * - ``getMrAddr() → int``
     - Returns the virtual address of the registered MR slab.
   * - ``getMrRkey() → int``
     - Returns the rkey of the registered MR.
   * - ``getMrLength() → int``
     - Returns the byte length of the MR slab.
   * - ``transitionToRtr(fpgaQpNum, fpgaGid) → None``
     - Transitions the host QP from INIT to RTR using the FPGA's QP
       number and GID.
   * - ``transitionToRts() → None``
     - Transitions the host QP from RTR to RTS.
   * - ``application(channelId) → stream.Master``
     - Returns the stream master for channel ``channelId`` (0–255).
   * - ``getRxFrameCount() → int``
     - Total frames received by the CQ polling thread.
   * - ``getRxByteCount() → int``
     - Total bytes received.
   * - ``getRxErrorCount() → int``
     - CQ error completion count.

Module-Level Constants
----------------------

Exposed via ``bp::scope().attr()`` in the module ``setup_python()``:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Constant
     - Description
   * - ``DefaultMaxPayload``
     - Default maximum payload per frame (bytes).  Typically ``8192``.
   * - ``DefaultRxQueueDepth``
     - Default number of receive slots.  Typically ``256``.

Usage from Python
-----------------

The C++ ``Server`` is normally not used directly — it is owned by
``RoCEv2Server``.  For low-level testing:

.. code-block:: python

    import rogue.protocols.rocev2 as rv2

    srv = rv2.Server('mlx5_0',
                     rxQueueDepth = rv2.DefaultRxQueueDepth,
                     maxPayload   = rv2.DefaultMaxPayload)

    print(f"QP num: {srv.getQpNum():#010x}")
    print(f"GID:    {srv.getGid()}")
    print(f"MR addr:{srv.getMrAddr():#018x}")
    print(f"MR rkey:{srv.getMrRkey():#010x}")

Build Dependencies
------------------

The C++ module requires:

* ``libibverbs`` (from ``rdma-core``, available on conda-forge)
* A C++17-capable compiler
* cmake ≥ 3.15

The module is compiled only when ``-DROCEV2=ON`` is passed to cmake (see
:doc:`../appendix/build`).  If ``rdma-core`` is not found, the RoCEv2 module
is silently skipped and the rest of rogue builds normally.

cmake Pattern
~~~~~~~~~~~~~

The ``rogue.protocols.rocev2`` cmake sub-directory uses an ``OBJECT``
library pattern to link ``libibverbs`` into the shared rogue library::

    # In protocols/rocev2/CMakeLists.txt
    find_package(IBVerbs REQUIRED)

    add_library(rogue-rocev2-obj OBJECT
        Server.cpp
        Core.cpp
    )
    target_include_directories(rogue-rocev2-obj PUBLIC
        ${CMAKE_SOURCE_DIR}/include
    )
    target_link_libraries(rogue-rocev2-obj PUBLIC IBVerbs::IBVerbs)

    # Propagate ibverbs to the parent rogue-core-shared target
    set(ROCEV2_EXTRA_LIBS IBVerbs::IBVerbs PARENT_SCOPE)

The parent ``CMakeLists.txt`` appends ``ROCEV2_EXTRA_LIBS`` to
``rogue-core-shared``'s link libraries.
