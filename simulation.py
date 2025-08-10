import time
import random
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# --- 1. SIMULATION LOGIC (FINALIZED WITH POWER METRIC PREPARATION) ---

# --- Configuration Constants ---
SIMULATION_STEPS = 100
SESSION_STATE_SIZE_MB = 100.0
NETWORK_BANDWIDTH_WIFI_MBps = 50.0
NETWORK_BANDWIDTH_5G_MBps = 25.0

# Granular power states
POWER_DRAIN_IDLE = 0.05
POWER_DRAIN_ACTIVE_HIGH_QOS = 0.20
POWER_DRAIN_ACTIVE_STD_QOS = 0.12
POWER_DRAIN_DECISION_CPU_BURST = 0.1
POWER_DRAIN_TX_WIFI = 0.3
POWER_DRAIN_TX_5G = 0.6

class Device:
    """Represents a user's device, modeling its state."""
    def __init__(self, name: str):
        self.name = name
        self.is_active = False
        self.is_prepared = False

class User:
    """Models the user's context and device ecosystem."""
    def __init__(self):
        self.devices = {"Laptop": Device("Laptop"), "Phone": Device("Phone")}
        self.context = "At Office"
        self.active_device_name = "Laptop"
        self.devices[self.active_device_name].is_active = True
        
    def switch_active_device(self, new_device_name: str, current_time: int):
        print(f"\n>>>> t={current_time}: USER ACTION: Switches from {self.active_device_name} to {new_device_name} <<<<")
        self.devices[self.active_device_name].is_active = False
        self.active_device_name = new_device_name
        self.devices[self.active_device_name].is_active = True
        
# --- Agent/Policy Implementations ---
class ReactiveAgent:
    """Baseline 1: Stays completely passive until user action."""
    def decide(self, udt):
        if udt['is_user_switching_now']:
            return {"action": "EXECUTE_MIGRATION"}
        return {}

class MyopicAgent:
    """Baseline 2: Adapts to the CURRENT state, but cannot predict the future."""
    def decide(self, udt):
        if udt['network_type'] == '5G' and udt['quality_level'] == 'High':
            return {"action": "ADJUST_QOS", "new_level": "Standard"}
        if udt['is_user_switching_now']:
            return {"action": "EXECUTE_MIGRATION"}
        return {}

class PASS_Agent:
    """The proactive agent implementing the PASS logic."""
    def __init__(self):
        self.sim_instance = None

    def _predict_intent(self, udt):
        """Simulates the LSTM prediction module."""
        if udt['user_context'] == 'Walking' and udt['active_device'] == 'Laptop':
            return "SWITCH_TO_PHONE"
        return "STAY"

    def decide(self, udt):
        """Simulates the DRL decision-making module."""
        prediction = self._predict_intent(udt)
        is_preparing = self.sim_instance.migration_in_progress and self.sim_instance.migration_in_progress['type'] == 'PREPARE'
        if prediction == "SWITCH_TO_PHONE" and not udt['devices']['Phone'].is_prepared and not is_preparing:
            return {"action": "PREPARE_MIGRATION"}
        if udt['is_user_switching_now']:
            return {"action": "EXECUTE_MIGRATION"}
        return {}

class Simulation:
    """Orchestrates the simulation of a nomadic user scenario."""
    def __init__(self, agent):
        self.user = User()
        self.agent = agent
        if hasattr(self.agent, 'sim_instance'): self.agent.sim_instance = self
        self.network_type = "Wi-Fi"
        self.network_bandwidth = NETWORK_BANDWIDTH_WIFI_MBps
        self.quality_level = "High"
        self.migration_in_progress = None
        self.metrics = {
            "handover_latency_steps": 0, "total_power_consumed": 0, "proactive_data_mb": 0,
            "total_migration_time": 0 # New metric for calculating throughput for Power
        }

    def _get_udt(self, is_switching=False):
        """Builds the User Digital Twin for the agent."""
        return {
            "user_context": self.user.context, "active_device": self.user.active_device_name,
            "devices": self.user.devices, "network_bandwidth": self.network_bandwidth,
            "network_type": self.network_type, "quality_level": self.quality_level,
            "is_user_switching_now": is_switching
        }

    def _execute_action(self, decision, current_time):
        action = decision.get("action", "NO_OP")
        
        # Track total migration time whenever a migration-related action is active
        if self.migration_in_progress:
            self.metrics["total_migration_time"] += 1

        if self.migration_in_progress:
            # Handle ongoing migration
            bw = self.migration_in_progress['bandwidth']
            tx_power_drain = POWER_DRAIN_TX_WIFI if self.migration_in_progress['network_type'] == 'Wi-Fi' else POWER_DRAIN_TX_5G
            self.metrics['total_power_consumed'] += tx_power_drain
            self.migration_in_progress['remaining_mb'] -= bw / 8.0
            if self.migration_in_progress['remaining_mb'] <= 0:
                print(f"INFO (t={current_time}): Migration ({self.migration_in_progress['type']}) completed in {self.migration_in_progress['steps_taken']} steps.")
                if self.migration_in_progress['type'] == 'PREPARE':
                    self.user.devices["Phone"].is_prepared = True
                    self.metrics["proactive_data_mb"] = SESSION_STATE_SIZE_MB
                else:
                    self.metrics["handover_latency_steps"] = self.migration_in_progress['steps_taken']
                self.migration_in_progress = None
            else:
                self.migration_in_progress['steps_taken'] += 1
            return

        # Start a new action
        if action in ["PREPARE_MIGRATION", "EXECUTE_MIGRATION"]:
             self.metrics["total_migration_time"] += 1

        if action == "PREPARE_MIGRATION":
            print(f"AGENT ACTION (t={current_time}): PREPARE_MIGRATION from Laptop to Phone")
            self.migration_in_progress = {"type": "PREPARE", "device": self.user.devices["Phone"], "remaining_mb": SESSION_STATE_SIZE_MB, "steps_taken": 1, "bandwidth": self.network_bandwidth, "network_type": self.network_type}
        elif action == "EXECUTE_MIGRATION":
            target_device = self.user.devices["Phone"]
            if target_device.is_prepared:
                print(f"AGENT ACTION (t={current_time}): EXECUTE_MIGRATION (Fast Path - Delta Sync)")
                self.metrics["handover_latency_steps"] = 1
            else:
                print(f"AGENT ACTION (t={current_time}): EXECUTE_MIGRATION (Slow Path - Full Sync)")
                self.migration_in_progress = {"type": "EXECUTE", "device": target_device, "remaining_mb": SESSION_STATE_SIZE_MB, "steps_taken": 1, "bandwidth": self.network_bandwidth, "network_type": self.network_type}
        elif action == "ADJUST_QOS":
            print(f"AGENT ACTION (t={current_time}): Myopic-Adaptive agent lowers QoS to '{decision['new_level']}' due to poor network.")
            self.quality_level = decision['new_level']
            self.metrics["total_power_consumed"] += POWER_DRAIN_DECISION_CPU_BURST

    def run(self):
        print(f"--- Starting Simulation for: {type(self.agent).__name__} ---")
        for t in range(SIMULATION_STEPS):
            is_switching_now = (t == 60)
            if t == 30:
                print(f"\n--- t={t}: CONTEXT CHANGE: User starts walking (Wi-Fi -> 5G) ---")
                self.user.context = "Walking"; self.network_type = "5G"; self.network_bandwidth = NETWORK_BANDWIDTH_5G_MBps
            if is_switching_now:
                self.user.switch_active_device("Phone", current_time=t)
            udt = self._get_udt(is_switching=is_switching_now)
            decision = self.agent.decide(udt)
            self._execute_action(decision, current_time=t)
            power_this_step = 0
            for dev in self.user.devices.values():
                power_this_step += (POWER_DRAIN_ACTIVE_HIGH_QOS if self.quality_level == "High" else POWER_DRAIN_ACTIVE_STD_QOS) if dev.is_active else POWER_DRAIN_IDLE
            self.metrics["total_power_consumed"] += power_this_step
        if self.migration_in_progress and self.migration_in_progress['type'] == 'EXECUTE':
            self.metrics["handover_latency_steps"] = self.migration_in_progress['steps_taken']
        return self.metrics

def run_all_simulations():
    print("=========================================\n=         RUNNING SIMULATIONS           =\n=========================================\n")
    results = {}
    for name, agent in {'Reactive': ReactiveAgent(), 'Myopic': MyopicAgent(), 'PASS': PASS_Agent()}.items():
        results[name] = Simulation(agent).run()
        print("\n" + "-"*45 + "\n")
    return results

# --- 2. VISUALIZATION LOGIC (WITH KLEINROCK'S POWER) ---
def generate_charts(results):
    print("\n=========================================\n=      GENERATING VISUALIZATIONS      =\n=========================================\n")
    if not os.path.exists('charts'):
        os.makedirs('charts')
        print("Created 'charts' directory for output.")

    agents = ['Reactive Baseline', 'Myopic-Adaptive', 'PASS Framework']
    metrics_map = {'Reactive Baseline': results['Reactive'], 'Myopic-Adaptive': results['Myopic'], 'PASS Framework': results['PASS']}
    
    # Calculate Kleinrock's Power for each framework before plotting
    for name, metrics in metrics_map.items():
        T = metrics['handover_latency_steps']
        T_for_calc = max(T, 1) # Use a small epsilon to avoid division by zero
        total_time = metrics['total_migration_time']
        gamma = (SESSION_STATE_SIZE_MB / total_time) if total_time > 0 else 0
        metrics['power'] = gamma / T_for_calc
    
    # --- Chart 1, 2, 3 (Latency, Timeline, QoE) ---
    # These functions are defined here but can be collapsed for brevity as they are unchanged.
    def plot_latency_chart():
        print("Generating Latency Comparison Chart...")
        latency = [m['handover_latency_steps'] for m in metrics_map.values()]
        plt.figure(figsize=(10, 6)); sns.set_theme(style="whitegrid")
        sns.barplot(x=agents, y=latency, hue=agents, palette=['#d9534f', '#f0ad4e', '#5cb85c'], dodge=False)
        plt.legend([],[], frameon=False)
        for i, v in enumerate(latency): plt.text(i, v + 0.5, str(v), ha='center', va='bottom', fontsize=14, fontweight='bold')
        plt.title('Comparison of User-Perceived Handover Latency', fontsize=16, fontweight='bold')
        plt.ylabel('Handover Latency (in Simulation Steps)', fontsize=12); plt.xlabel('Framework Type', fontsize=12)
        plt.ylim(0, max(latency) * 1.15 if max(latency) > 0 else 10)
        plt.savefig('charts/handover_latency_comparison.pdf', bbox_inches='tight'); plt.close()
        print("Saved 'charts/handover_latency_comparison.pdf'")
    
    def plot_timeline_chart():
        # ... [Full timeline plotting code from previous answer] ...
        print("Generating Event Timeline Chart...")
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True, gridspec_kw={'hspace': 0.5})
        fig.suptitle('Event Timeline: Comparison of Frameworks', fontsize=16, fontweight='bold')
        # ... [The inner plot_timeline function] ...
        def plot_timeline_inner(ax, title, metrics, is_pass=False):
            ax.set_title(title, loc='left', fontsize=12, fontweight='bold')
            ax.set_ylim(0, 1); ax.set_yticks([]); ax.set_xlim(-5, 105)
            ax.axvline(30, color='grey', linestyle='--', label='Context Change'); ax.axvline(60, color='black', linestyle='-', label='User Switch')
            ax.text(15, 0.5, 'Normal Operation\n(Wi-Fi)', ha='center', va='center', alpha=0.7)
            if is_pass:
                prep_duration = int(SESSION_STATE_SIZE_MB / (NETWORK_BANDWIDTH_WIFI_MBps / 8.0))
                prep_end = 30 + prep_duration
                ax.fill_betweenx([0.2, 0.8], 30, prep_end, color='#5bc0de', alpha=0.6, label='Background Preparation')
                ax.text((30 + prep_end) / 2, 0.5, f"Proactive Transfer\n({prep_duration} steps on Wi-Fi)", ha='center', va='center', color='black', fontsize=9)
                ax.fill_betweenx([0.2, 0.8], 60, 60 + metrics['handover_latency_steps'], color='#5cb85c', alpha=0.7, label='Near-Zero Latency')
                ax.text(80, 0.5, 'Session Ready\n& Active', ha='center', va='center', alpha=0.7)
            else:
                ax.text(45, 0.5, 'Normal Operation\n(5G)', ha='center', va='center', alpha=0.7)
                latency_end = 60 + metrics['handover_latency_steps']
                ax.fill_betweenx([0.2, 0.8], 60, latency_end, color='#d9534f', alpha=0.6, label='User Waiting (Latency)')
                ax.text((60 + latency_end) / 2, 0.5, f"Full State Transfer\n({metrics['handover_latency_steps']} steps on 5G)", ha='center', va='center', color='white', fontsize=9, fontweight='bold')
                ax.text(latency_end + 10, 0.5, 'Session Ready', ha='center', va='center', alpha=0.7)
        plot_timeline_inner(ax1, 'Reactive Baseline Framework', metrics_map['Reactive Baseline'])
        plot_timeline_inner(ax2, 'Myopic-Adaptive Framework', metrics_map['Myopic-Adaptive'])
        plot_timeline_inner(ax3, 'PASS Framework', metrics_map['PASS Framework'], is_pass=True)
        ax1.legend(loc='upper left'); ax2.legend_ = None; ax3.legend_ = None
        ax3.set_xlabel('Simulation Time (steps)', fontsize=12)
        fig.tight_layout(); fig.subplots_adjust(top=0.94)
        plt.savefig('charts/event_timeline_comparison.pdf'); plt.close()
        print("Saved 'charts/event_timeline_comparison.pdf'")

    def plot_qoe_chart():
        # ... [Full QoE plotting code from previous answer] ...
        print("Generating QoE over Time Chart...")
        QOE_EXCELLENT, QOE_POOR = 5, 1.5; time_steps = np.arange(SIMULATION_STEPS)
        def calculate_qoe_curve(metrics):
            qoe_curve = np.full_like(time_steps, QOE_EXCELLENT, dtype=float)
            if metrics['handover_latency_steps'] > 1:
                start_idx, end_idx = 60, min(60 + metrics['handover_latency_steps'], SIMULATION_STEPS)
                qoe_curve[start_idx : end_idx] = QOE_POOR
            return qoe_curve
        qoe_curves = {'Reactive Baseline': (calculate_qoe_curve(metrics_map['Reactive Baseline']), '#d9534f', '--'), 'Myopic-Adaptive': (calculate_qoe_curve(metrics_map['Myopic-Adaptive']), '#f0ad4e', ':'), 'PASS Framework': (calculate_qoe_curve(metrics_map['PASS Framework']), '#5cb85c', '-')}
        sns.set_theme(style="darkgrid"); plt.figure(figsize=(12, 6))
        for label, (curve, color, style) in qoe_curves.items(): plt.plot(time_steps, curve, label=label, color=color, linestyle=style, linewidth=2.5)
        plt.axvline(x=30, color='grey', linestyle='--', label='Context Change'); plt.axvline(x=60, color='black', linestyle='-', label='User Switch')
        plt.title('Quality of Experience (QoE) Over Time', fontsize=16, fontweight='bold')
        plt.xlabel('Simulation Time (steps)', fontsize=12); plt.ylabel('QoE Score (1-5 Scale)', fontsize=12)
        plt.legend(fontsize=11); plt.ylim(0, 5.5)
        plt.savefig('charts/qoe_over_time.pdf', bbox_inches='tight'); plt.close()
        print("Saved 'charts/qoe_over_time.pdf'")

    # --- NEW Chart 4: Kleinrock's Power Comparison ---
    def plot_power_chart():
        print("Generating Kleinrock's Power Comparison Chart...")
        power_values = [m['power'] for m in metrics_map.values()]
        plt.figure(figsize=(10, 6)); sns.set_theme(style="whitegrid")
        sns.barplot(x=agents, y=power_values, hue=agents, palette=['#d9534f', '#f0ad4e', '#5cb85c'], dodge=False)
        plt.legend([],[], frameon=False)
        for i, v in enumerate(power_values): plt.text(i, v, f'{v:.2f}', ha='center', va='bottom', fontsize=12, fontweight='bold')
        plt.ylabel("Kleinrock's Power (γ / T)", fontsize=12); plt.xlabel('Framework Type', fontsize=12)
        plt.title("Comparison of System Efficiency (Kleinrock's Power)", fontsize=16, fontweight='bold')
        plt.savefig('charts/kleinrock_power_comparison.pdf', bbox_inches='tight'); plt.close()
        print("Saved 'charts/kleinrock_power_comparison.pdf'")

    # Execute all plotting functions
    plot_latency_chart()
    plot_timeline_chart()
    plot_qoe_chart()
    plot_power_chart()
    
    print("\nAll visualization tasks completed.")

if __name__ == "__main__":
    results = run_all_simulations()
    
    # Calculate Power metric before printing summary
    for metrics in results.values():
        T = metrics['handover_latency_steps']; T_for_calc = max(T, 1)
        total_time = metrics['total_migration_time']
        gamma = (SESSION_STATE_SIZE_MB / total_time) if total_time > 0 else 0
        metrics['power'] = gamma / T_for_calc

    print("--- FINAL RESULTS SUMMARY (WITH POWER METRIC) ---")
    header = f"{'Metric':<30} | {'Reactive':<15} | {'Myopic':<15} | {'PASS':<15}"
    print(header + "\n" + "-" * len(header))
    r, m, p = results['Reactive'], results['Myopic'], results['PASS']
    print(f"{'Handover Latency (steps)':<30} | {r['handover_latency_steps']:<15} | {m['handover_latency_steps']:<15} | {p['handover_latency_steps']:<15}")
    print(f"{'Total Power Consumed (units)':<30} | {r['total_power_consumed']:<15.2f} | {m['total_power_consumed']:<15.2f} | {p['total_power_consumed']:<15.2f}")
    print(f"{'Kleinrock\'s Power (γ/T)':<30} | {r['power']:<15.2f} | {m['power']:<15.2f} | {p['power']:<15.2f}")
    print(f"{'Proactive Data (MB)':<30} | {r['proactive_data_mb']:<15.2f} | {m['proactive_data_mb']:<15.2f} | {p['proactive_data_mb']:<15.2f}")
    
    generate_charts(results)