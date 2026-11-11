# TG-THERMAL — Halo R-Series Thermal Design Guide

> Fictional company and products, created for a portfolio project.

## Limits
Maximum junction temperature is 125 °C for all Halo R-Series retimers.

## HX-R6016
A heatsink is required. Operation without a heatsink is not supported. With the standard heatsink, provide at least 200 LFM of airflow at 55 °C inlet air temperature.

## HX-R5016
With the standard heatsink, provide at least 150 LFM of airflow at 55 °C inlet. Without a heatsink, operation is supported only at or below 35 °C inlet.

## Throttling
If the junction approaches 125 °C, the retimer raises a thermal alert over SMBus. It does not throttle the link speed on its own.
