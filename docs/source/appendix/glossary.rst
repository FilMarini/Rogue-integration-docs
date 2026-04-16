Glossary
========

.. glossary::

   AXI-lite
      A lightweight subset of the AXI (Advanced eXtensible Interface) bus
      protocol commonly used for slow-path register access in FPGA designs.
      Supports single read and write transactions with no burst capability.

   BSV
      Bluespec SystemVerilog.  A high-level hardware description language
      used by SLAC for the RoCEv2 engine firmware.

   CNP
      Congestion Notification Packet.  A special RoCEv2 packet sent by the
      receiver NIC when it detects an ECN-marked packet.  Used by DCQCN to
      signal the sender to reduce its rate.

   CQ
      Completion Queue.  An libibverbs data structure that the NIC (or FPGA)
      fills with completion entries (CQEs) after finishing a work request.
      The host polls the CQ to know when an RDMA WRITE has been received.

   CQE
      Completion Queue Entry.  A single record in a :term:`CQ` describing
      the outcome of a work request (opcode, byte count, immediate value,
      status).

   DCQCN
      Data Center Quantized Congestion Notification.  A hardware-based
      congestion control algorithm for RoCEv2 networks.  Described in
      Zhu et al., SIGCOMM 2015.

   ECN
      Explicit Congestion Notification.  An IP/TCP mechanism where a switch
      marks packets (rather than dropping them) to signal congestion.
      RoCEv2 relies on ECN for DCQCN congestion signals.

   GID
      Global Identifier.  A 128-bit identifier for an RDMA endpoint,
      equivalent to an IPv6 address.  For RoCEv2 over IPv4, the GID is
      derived as the IPv4-mapped IPv6 address ``::ffff:<ipv4>``.

   IBV
      InfiniBand Verbs.  The userspace API (``libibverbs``) for programming
      RDMA operations.  Used on the host side in this integration.

   libibverbs
      The userspace library implementing the InfiniBand Verbs API.  Part of
      the ``rdma-core`` package.

   lkey
      Local Key.  A 32-bit key associated with a Memory Region that
      authorises local DMA access.  Assigned by the FPGA resource manager.

   MR
      Memory Region.  A range of host virtual memory registered with the
      RDMA NIC, allowing the NIC to DMA into it.  The :term:`rkey`
      authorises remote write access; the :term:`lkey` authorises local
      access.

   MTU
      Maximum Transmission Unit.  The largest payload size for a single
      RDMA packet.  For 10 GbE links, ``IBV_MTU_4096`` (4096 bytes) is
      recommended.

   PD
      Protection Domain.  An libibverbs / FPGA resource that groups MRs and
      QPs.  Provides access isolation — a QP can only access MRs in its own
      PD.

   PSN
      Packet Sequence Number.  A 24-bit counter used for RDMA packet ordering
      and duplicate detection.  Both endpoints initialise their PSN at QP
      creation.

   QP
      Queue Pair.  The fundamental RDMA communication endpoint.  Consists of
      a Send Queue (SQ) and a Receive Queue (RQ).  In this integration, the
      FPGA uses an RC QP as the initiator; the host has a matching RC QP as
      the target.

   RC
      Reliable Connected.  An RDMA transport type providing ordered,
      error-checked, point-to-point delivery.  Required for RDMA WRITE
      operations.

   RDMA
      Remote Direct Memory Access.  A technique allowing a remote device
      (here: the FPGA) to read or write host memory without involving the
      host CPU on the data path.

   RDMA WRITE-with-Immediate
      An RDMA operation where the initiator (FPGA) writes data into the
      target's (host's) memory and also delivers a 32-bit immediate value
      to the target's Completion Queue.  The immediate value is used here
      to carry the channel ID.

   rkey
      Remote Key.  A 32-bit key associated with a :term:`MR` that must be
      presented by a remote initiator to perform RDMA WRITEs into that MR.
      The host communicates its rkey to the FPGA during the connection
      handshake.

   RoCEv2
      RDMA over Converged Ethernet, version 2.  Carries IB transport
      semantics over standard Ethernet/IP/UDP frames.  Enables RDMA on
      commodity 10 GbE and above networks.

   rogue
      SLAC's software framework for FPGA interfacing.
      `https://github.com/slaclab/rogue <https://github.com/slaclab/rogue>`_

   RNR NAK
      Receiver Not Ready Negative Acknowledgement.  Sent by the receive
      side when it cannot accept a packet (e.g. no receive buffers posted).
      In this integration, the host does not post receive buffers (the FPGA
      WRITEs directly into the MR), so RNR NAKs should not occur during
      normal operation.

   SoftRoCE
      A software implementation of RoCEv2 built into the Linux kernel
      (kernel module ``rdma_rxe``).  It emulates a RoCEv2 RDMA device on
      top of any standard Ethernet NIC, allowing RDMA development and
      testing without dedicated RDMA hardware.  Activated with
      ``sudo modprobe rdma_rxe`` and
      ``sudo rdma link add rxe0 type rxe netdev <interface>``.

   SRP
      SLAC Register Protocol.  The protocol used by rogue for AXI-lite
      register access over UDP.

   SSI
      SLAC Streaming Interface.  The sideband signalling convention used
      by rogue stream frames.  ``firstUser[1] = 1`` (value ``0x2``) marks
      the Start Of Frame.

   UD
      Unreliable Datagram.  An RDMA transport type providing
      connectionless, best-effort delivery.  Does **not** support RDMA
      WRITE; only SEND/RECEIVE operations.  Not used in this integration.
