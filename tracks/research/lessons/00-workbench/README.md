---
id: 00
title: The workbench
---

# Module 00 - The workbench

This module sets up the bench every experiment of the track runs on. It starts with one whole experiment in one short file: twenty noisy points of a sine wave, a cubic with four weights, a loss that says how wrong the cubic is, its gradient worked out by hand, gradient descent, and a score on five hundred points the fit never saw. Every job the track later builds a part for is done there once, small and by hand. Then it builds the first piece of the lab, the runner: settings changed from the command line, a seed that decides every random number a run draws, and a folder for each run holding its settings, its log and its result, the same bytes each time the run is repeated. Last, it runs the same fit with five seeds and finds that the seed alone moves the test loss from 0.047 to 0.065, so the lab learns to report a result as its mean and spread over seeds, to tell two settings apart with Welch's t, and to draw every run's curve from its log. After this module every number the track reports is a set of runs over several seeds, with its spread, that anyone can run again. It stands on nothing: the track starts here.
