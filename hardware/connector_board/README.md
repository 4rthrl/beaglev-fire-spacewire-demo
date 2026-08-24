# SpaceWire Interface Board

This PCB is a compact SpaceWire interface board designed for use with the **BeagleV-Fire** platform through its SYZYGY connector.

The board converts FPGA logic-level Data and Strobe signals to/from LVDS for connection to a standard **9-pin Micro-D SpaceWire connector**. It is designed for SpaceWire data rates up to **400 Mbit/s**.

## Main features

- BeagleV-Fire / SYZYGY interface
- SpaceWire Data + Strobe transmit and receive
- Designed for up to **400 Mbit/s**
- 100 Ω differential SpaceWire routing
- Dual LVDS transmitter: **DS90LV027A**
- Dual LVDS receiver: **DS90LVRA2-Q1**
- 1.8 V / 3.3 V level translation for the FPGA interface
- 9-pin Micro-D SpaceWire connector
- 4-layer PCB with controlled-impedance differential routing

## SYZYGY compatibility

The board uses the standard SYZYGY physical connector and BeagleV-Fire pin interface, but it is **not intended to be a fully compliant generic SYZYGY peripheral**.

In particular, the board does not include the SYZYGY programming / identification circuitry or headers required for automatic SmartVIO configuration. It is intended specifically as a dedicated SpaceWire interface for the BeagleV-Fire setup.

## Purpose

The board was developed as part of a SpaceWire integration project to provide a clean physical interface between the BeagleV-Fire FPGA fabric and external SpaceWire equipment.
