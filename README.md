# Football Play Similarity – Analyst Track Abstract

## Introduction

Comparing football plays using tracking data is a challenging task due to their high dimensionality, temporal dependency, and natural variability in execution. Traditional similarity methods based on event labels or fixed-length representations often fail to capture the underlying spatiotemporal structure of a play. Even trajectory-based approaches face difficulties when comparing plays of different durations and tempos.

Football Play Similarity addresses these challenges through a trajectory-driven approach centered on ball movement during player possession events. The solution applies **Dynamic Time Warping (DTW)** to align and compare trajectories in a way that is robust to temporal distortion and variable play lengths.

## Usecase(s)

The solution extracts all play sequences from a given SkillCorner dataset and computes pairwise similarity between their ball trajectories sampled at player possession events. Using possession-based sampling provides a compact, event-aligned representation of each play while preserving its tactical structure.

To enable comparison between sequences of unequal duration, longer plays are subdivided into non-overlapping sub-sequences matching the length of the shorter play. DTW is computed between the shorter trajectory and each sub-sequence of the longer one, allowing partial alignment and meaningful similarity measurement across variable-length plays.

The resulting similarity matrix enables clustering and retrieval of structurally similar plays, supporting tactical pattern discovery, comparison of play execution across teams or matches, and exploratory analysis without manual labeling or predefined play types.

## Potential Audience

This solution is designed for football analysts and data scientists working with SkillCorner tracking data, performance and opposition analysts seeking automated play pattern discovery, and researchers applying time-series similarity methods to football analytics.
