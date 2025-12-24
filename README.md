# *Identifying Similar Football Plays Through Ball Movement Patterns*
#### A DTW-Based Trajectory Similarity Approach Using SkillCorner Open Data - Analyst Track Abstract

## Introduction

Extracting similar plays to a given football play from tracking data is a challenging task due to the high dimensionality, temporal dependency, and natural variability in execution.
Traditional similarity methods often fail to capture the underlying spatiotemporal structure of a play. Even trajectory-based approaches face difficulties when comparing plays of different durations and tempos.

*Identifying Similar Football Plays Through Ball Movement Patterns* addresses these challenges through a trajectory-driven approach centered on ball movement during **player possession events**. The proposed method applies **Dynamic Time Warping (DTW)** to align and compare ball trajectories in a way that is robust to temporal distortion and variable play lengths. By computing similarity scores across extracted plays, the approach enables the retrieval of the **top-N most similar football plays for any given play**, supporting efficient exploration of recurring movement patterns and alternative play executions.

## Usecase(s)

The solution extracts all play sequences from a given SkillCorner dataset and computes pairwise similarity between their ball trajectories sampled at player possession events. Using possession-based sampling provides a compact, event-aligned representation of each play while preserving its tactical structure.

To enable comparison between sequences of unequal duration, longer plays are subdivided into non-overlapping sub-sequences matching the length of the shorter play. DTW is computed between the shorter trajectory and each sub-sequence of the longer one, allowing partial alignment and meaningful similarity measurement across variable-length plays.

The resulting similarity scores allow analysts and coaches to retrieve the **top-N most similar plays** for any selected play, enabling clustering, tactical pattern discovery, comparison of play execution across teams or matches, and exploratory analysis without manual labeling or predefined play types.

## Potential Audience

This solution is designed for football analysts, coaches, and data scientists working with tracking/events data, performance and opposition analysts seeking automated play pattern discovery, and researchers applying time-series similarity methods to football analytics.

---

## Video URL

<p align="center">
  <a href="https://drive.google.com/file/d/1yF34XMzFlEv5nQqV2ximnH-tGXCLCINZ/view?usp=sharing">Watch Video</a>
</p>


---

## Run Instructions

### 1. Install Dependencies
Make sure you have **Python 3.11** and **pip** installed.  
Install required packages:

```bash
pip install pandas numpy scikit-learn fastdtw scipy
```
### 2. Download Data
The notebook will automatically download match event and tracking data from SkillCorner OpenData.
No manual download is needed.

### 3. Run The Pipeline

Open `Data_preprocessing_and_similarity_score_calculation.ipynb`.

Run each cell in order:

1. **Setup and configuration**  
2. **Export event sequences for all matches**  
3. **Extract ball positions for all sequences**  
4. **Normalize and convert data for similarity scoring**
5. **Compute DTW similarity matrix**
6. **Export top-N similar plays for website integration**

### 4. Website Integration

After running the notebook, JSON files for similar plays will be saved in: website/public/<MATCH_ID>/

These files can be used directly by the website.

**Tip:**  
- To change the number of events per sequence or the target match for similarity search, edit the relevant configuration variables in the notebook cells.  
- Make sure to adjust `manifest.json` with the match's sequences IDs.  
- Included is the `manifest.json` for match **1886347** for **10 Events Sequences**.

### 5. Run the Website

#### a. Install Node.js dependencies
Open a terminal in the `website` folder and run:

```bash
npm install
npm run dev
```
---

## URL to Web App / Website
<p align="center">
  <a href="https://football-similarity.netlify.app/">URL to Web App / Website</a>
</p>
