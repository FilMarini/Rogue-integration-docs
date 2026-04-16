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

RDMA Device Check
-----------------

.. code-block:: bash

    # List RDMA devices on the host
    ibv_devices

    # Show device details (GID table, port state)
    ibv_devinfo -d mlx5_0

    # Verify RoCEv2 mode (should show RoCE v2 in GID table)
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


RDMA Device Check
-----------------

.. code-block:: bash

    # List RDMA devices on the host
    ibv_devices

    # Show device details (GID table, port state)
    ibv_devinfo -d mlx5_0

    # Verify RoCEv2 mode (should show RoCE v2 in GID table)
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
