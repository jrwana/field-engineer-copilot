# PB-MEMORY — Halo M2 CXL Memory Controller (Product Brief)

> Fictional company and products, created for a portfolio project.

## Overview
The HX-M2200 is a CXL 2.0 Type 3 memory controller. It connects DDR5 memory to a host over a PCIe 5.0 x16 / CXL 2.0 link, adding memory capacity and bandwidth beyond the CPU's own DIMM slots.

## Memory configuration
Two DDR5 channels, up to DDR5-5600. Up to 2 TB of memory per controller. Inline ECC is supported. Peak bandwidth is up to 64 GB/s.

## Latency
The HX-M2200 adds a typical load-to-use latency of 85 ns compared with local DRAM attached directly to the CPU.

## Multi-host and pooling
With CXL 2.0 hosts, the HX-M2200 supports hot-plug and can operate as a multi-logical device (MLD), shared by up to 4 hosts through a CXL 2.0 switch. See AN-310 for host requirements.

## Power
Typical power is 14 W, excluding the DIMMs.
