# PB-RETIMER — Halo R-Series PCIe/CXL Smart Retimers (Product Brief)

> Fictional company and products, created for a portfolio project.

## Overview
The Halo R-Series retimers extend PCIe and CXL links across long board traces, risers and cables. A retimer fully recovers and retransmits the signal, which splits one long channel into two shorter segments, each with its full loss budget. Three generations are offered: Halo R4 (PCIe 4.0), Halo R5 (PCIe 5.0, CXL 2.0) and Halo R6 (PCIe 6.0, CXL 3.1).

## Part numbers and status
HX-R4016 (PCIe 4.0 x16) is end-of-life (EOL); new designs should use HX-R5016. HX-R5008 (x8) and HX-R5016 (x16) are in production. HX-R6016 (PCIe 6.0 x16) is in production. HX-R6008 (PCIe 6.0 x8) is sampling to selected customers and is not yet in volume production.

## Latency
Typical added latency per direction: 12 ns for Halo R4, 10 ns for Halo R5, and 9 ns for Halo R6 in FLIT mode. Halo R6 uses PCIe 6.0 FLIT mode with PAM4 signaling at 64 GT/s.

## Backward compatibility
All Halo R-Series retimers are backward compatible with earlier PCIe generations down to PCIe 1.0. For example, an HX-R6016 placed between a PCIe 6.0 host and a PCIe 5.0 SSD will train the link at the highest common rate, 32 GT/s. The retimer is protocol-transparent and works with any PCIe-compliant root complex and endpoint.

## Diagnostics
Halo R5 and Halo R6 support receiver lane margining and per-lane eye diagnostics through the Halo Link Insight software (see AN-204). Halo R4 does not support lane margining.

## CXL support
Halo R5 supports CXL 1.1 and 2.0. Halo R6 supports CXL 1.1, 2.0, 3.0 and 3.1. Halo R4 has no CXL support.
