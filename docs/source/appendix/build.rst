Building Rogue with RoCEv2 Support
====================================

Prerequisites
-------------

.. code-block:: bash

    # With conda / mamba (recommended)
    conda install -c conda-forge rdma-core cmake boost python numpy

    # Or on Ubuntu with MLNX_OFED installed:
    apt-get install libibverbs-dev librdmacm-dev

    # Verify ibverbs is found:
    pkg-config --modversion libibverbs

cmake Configuration
-------------------

The RoCEv2 module is enabled by passing ``-DROCEV2=ON`` to cmake.  If the
flag is not set, the module is not compiled even if ``libibverbs`` is
present on the system:

.. code-block:: bash

    git clone https://github.com/slaclab/rogue.git
    cd rogue
    mkdir build && cd build

    cmake .. \
        -DROCEV2=ON \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=$CONDA_PREFIX

    make -j$(nproc)
    make install

If ``libibverbs`` / ``rdma-core`` is not found when ``-DROCEV2=ON`` is set,
cmake will exit with an error.

Verifying the Build
-------------------

.. code-block:: python

    import rogue.protocols.rocev2 as rv2
    print(rv2.DefaultMaxPayload)       # e.g. 8192
    print(rv2.DefaultRxQueueDepth)     # e.g. 256

    import pyrogue.protocols
    print(dir(pyrogue.protocols))      # should include RoCEv2Server

RDMA Hardware Requirement
--------------------------

A dedicated RDMA-capable NIC (e.g. Mellanox/NVIDIA ConnectX) is **not
required** for development and testing.  Any standard Ethernet NIC can be
used via **SoftRoCE** (``rdma_rxe``), a software RDMA implementation built
into the Linux kernel that emulates a RoCEv2 device on top of a regular
network interface.

SoftRoCE is fully supported by ``libibverbs`` and is transparent to the
rogue RoCEv2 module — the same code runs unchanged on both SoftRoCE and
hardware RDMA NICs.

.. note::
   SoftRoCE involves the kernel on the data path, so it does not deliver the
   zero-copy, kernel-bypass latency of a hardware NIC.  It is suitable for
   functional testing and development but not for production high-rate use.

Setting Up SoftRoCE
--------------------

**1. Load the kernel module**

The SoftRoCE driver is included in the mainline Linux kernel (``rdma_rxe``).
Load it with:

.. code-block:: bash

    sudo modprobe rdma_rxe

To load it automatically on boot:

.. code-block:: bash

    echo "rdma_rxe" | sudo tee /etc/modules-load.d/rdma_rxe.conf

Verify the module is loaded:

.. code-block:: bash

    lsmod | grep rdma_rxe

**2. Identify the Ethernet interface**

Find the name of the Ethernet interface you want to attach SoftRoCE to:

.. code-block:: bash

    ip link show
    # or
    ifconfig -a

The interface must be **up** and have an IP address assigned.  For example,
if your interface is ``eth0`` and the FPGA is connected to it:

.. code-block:: bash

    # Confirm the interface is up and has an IP
    ip addr show eth0

**3. Create the SoftRoCE link**

Attach a SoftRoCE device (``rxe0``) to the Ethernet interface:

.. code-block:: bash

    sudo rdma link add rxe0 type rxe netdev eth0

Replace ``eth0`` with your actual interface name.  The ``rxe0`` name is
conventional but can be anything.

Verify the device was created:

.. code-block:: bash

    rdma link show
    # Expected output:
    # link rxe0/1 state ACTIVE physical_state POLLING netdev eth0

    ibv_devices
    # Expected output:
    # device          node GUID
    # ------          ----------------
    # rxe0            <guid>

**4. Verify the GID**

Check that the GID table shows the IPv4-mapped address:

.. code-block:: bash

    ibv_devinfo -d rxe0 -v | grep -A5 "GID"
    # or
    show_gids   # from rdma-core

The GID for port 1 index 0 should be ``::ffff:<host_ip>``, e.g.
``::ffff:192.168.2.1``.  This is what the rogue ``RoCEv2Server`` uses to
derive the host GID automatically.

**5. Use SoftRoCE in rogue**

Pass ``rxe0`` as the ``rdmaDevice`` argument (or ``--roceDevice rxe0`` if
your startup script exposes it as a CLI argument):

.. code-block:: python

    rdma = pyrogue.protocols.RoCEv2Server(
        name         = 'rdmaRx',
        ip           = '192.168.2.10',   # FPGA IP
        rdmaDevice   = 'rxe0',           # SoftRoCE device
        rxQueueDepth = 256,
        maxPayload   = 8192,
    )

**Removing the SoftRoCE link**

To remove the SoftRoCE device when no longer needed:

.. code-block:: bash

    sudo rdma link delete rxe0/1

RDMA Device Check
-----------------

Once a device is available (hardware NIC or SoftRoCE), verify it is
accessible:

.. code-block:: bash

    # List RDMA devices on the host
    ibv_devices

    # Show device details (GID table, port state)
    ibv_devinfo -d rxe0      # or mlx5_0 for hardware NIC

    # Verify RoCEv2 mode (GID table should show IPv4-mapped addresses)
    show_gids    # from rdma-core tools

The GID at index 0 of port 1 should be the IPv4-mapped address
``::ffff:<host_ip>`` when RoCEv2 mode is active.

Conda Environment File
-----------------------

A complete environment for building and running the RoCEv2 integration:

.. code-block:: yaml

    # environment.yml
    name: rogue-rocev2
    channels:
      - conda-forge
      - defaults
    dependencies:
      - python=3.11
      - cmake>=3.15
      - boost>=1.75
      - numpy
      - pyzmq
      - rdma-core
      - pip
      - pip:
          - pyrogue

Save as ``environment.yml`` and create with::

    mamba env create -f environment.yml
    conda activate rogue-rocev2
