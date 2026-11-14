---
id: 08
title: Finding the way: route
---

# Module 08 - Finding the way: route

This module builds route, which finds the shortest way between two junctions of a real road map, central London from OpenStreetMap, prints it junction by junction and draws it. It reads the map into adjacency lists, so that a junction's roads cost their number to find instead of a read of the whole map, and uses them first to find the map's connected pieces. Then come three searches, each a fix for the one before: breadth-first search, which finds the route with the fewest junctions, and on London a longer one than it needs; Dijkstra's algorithm, which finishes junctions in order of metres and keeps the nearest one waiting on top of the heap built in module 02, instead of looking at every junction for it; and A*, which adds to each junction's distance the straight line still to go, and so finds the same shortest route after finishing a narrow band of the map instead of a disc around the start. After this module route answers a request for a route on a map of any size, and the slow ways stay runnable beside the fast ones, so the difference is measured on your machine, on London and on made-up cities of up to two million junctions.
