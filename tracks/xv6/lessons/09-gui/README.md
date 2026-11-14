---
id: 09
title: GUI
optional: true
---

# Module 09 - GUI

A screen, a keyboard and a mouse, and a paint program to use them. The kernel sets up QEMU's ramfb framebuffer through fw_cfg and maps it into any process that asks, drives two more virtio devices for the keyboard and the mouse, and hands their events to programs through a device file; a small library in user space draws rectangles, lines and text. It stands on page tables (02.04), the virtio queues of the disk (05.01), device files (05.07) and fork and exit (06.04); nothing in the rest of the kernel depends on it.
