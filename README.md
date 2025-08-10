# Official Simulation Code for PASS Framework

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository contains the Python simulation code for the research paper:

**PASS: A Predictive and Adaptive Session Synchro-migration Framework for Nomadic Computing using Deep Reinforcement Learning and Digital Twins**

This simulation models the core logic of the PASS framework and compares its performance against two baselines (Reactive and Myopic-Adaptive) in a defined nomadic computing scenario.

## About the PASS Framework

PASS is a novel framework designed to address the challenge of seamless session continuity in modern, multi-device computing environments. It transforms session migration from a disruptive, reactive process into a smooth, proactive service. This is achieved by using a **User Digital Twin (UDT)** to model the user's holistic context and a **hybrid AI engine** (conceptually modeled as an LSTM for prediction and a DRL agent for decision-making) to anticipate user needs and prepare for device handovers *before* they occur.

## The Simulation Scenario

The script simulates a typical knowledge worker's routine, creating a dynamic environment to test each framework's adaptability.

### User Journey & Context Changes

The simulation runs for 100 discrete time steps and includes two critical events:
1.  **`t=30` (Context Change):** The user, initially `At Office` and connected to a high-speed `Wi-Fi` network (50 MBps), stands up and begins `Walking`. This triggers a network switch to a `5G` connection (25 MBps). This event is the primary signal for the PASS framework's predictive module.
2.  **`t=60` (Device Switch):** The user explicitly decides to switch from their `Laptop` to their `Phone` to continue their work. This is the moment where handover latency is measured.

### Key Parameters
- **Session State Size:** 100 MB
- **Network Bandwidths:**
    - Wi-Fi: 50.0 MBps
    - 5G: 25.0 MBps
- **Power Consumption:** The model includes granular power drain states for idle, active use, CPU bursts, and data transmission over Wi-Fi vs. 5G.

## Frameworks Compared

The simulation implements and compares three distinct agents:

1.  **`ReactiveAgent`:** A baseline that models current commercial systems (e.g., Apple Handoff). It remains completely passive until the user initiates the device switch at `t=60`.
2.  **`MyopicAgent`:** A more advanced baseline that can adapt to its current context (e.g., adjust QoS) but lacks predictive foresight. It cannot anticipate the user's intent to switch devices.
3.  **`PASS_Agent`:** The full implementation of our proposed framework. It uses a simulated LSTM to predict the user's intent to switch devices after the context change at `t=30` and a simulated DRL agent to proactively initiate the session migration in the background.

## Requirements

The simulation script requires the following Python libraries:
- `matplotlib`
- `seaborn`
- `numpy`

You can install them using pip:
```bash
pip install matplotlib seaborn numpy
```

## How to Run

1.  Clone this repository:
```bash
    git https://github.com/xifezhao/Pass.git
    cd Pass
```
2.  Run the Python script:
```bash
    python simulation.py
```

## Expected Output

The script will:
1.  Print a detailed, step-by-step log of the simulation for each of the three frameworks to the console.
2.  Print a final summary table comparing the key performance metrics.
3.  Generate and save four publication-quality charts to a newly created `/charts` directory.

### Final Results Summary

The console will output the following summary table, demonstrating the superior performance of the PASS framework:

```
----------------------------------------------------------------------------------
Metric                         | Reactive        | Myopic          | PASS           
----------------------------------------------------------------------------------
Handover Latency (steps)       | 32              | 32              | 1              
Total Power Consumed (units)   | 26.90           | 26.90           | 24.40          
Kleinrock's Power (γ/T)        | 0.10            | 0.10            | 6.25           
Proactive Data (MB)            | 0.00            | 0.00            | 100.00         
```

## Generated Charts

The following charts will be saved as PDF files in the `/charts` directory.

### 1. User-Perceived Handover Latency

*(Representative image of `handover_latency_comparison.pdf`)*

### 2. Event Timeline Comparison

*(Representative image of `event_timeline_comparison.pdf`)*

### 3. Quality of Experience (QoE) Over Time

*(Representative image of `qoe_over_time.pdf`)*

### 4. System Efficiency (Kleinrock's Power)

*(Representative image of `kleinrock_power_comparison.pdf`)*

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
