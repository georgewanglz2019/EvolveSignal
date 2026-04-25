"""Traffic-signal control (fixed lane layout and phase sequence)"""

# === Fixed lane configuration ===
LANES_THROUGH = 2           # Number of dedicated through lanes per approach
LANES_LEFT = 1              # Number of dedicated left-turn lanes per approach
LANES_THROUGH_RIGHT = 1     # Number of shared through–right lanes per approach

# === Fixed control parameters ===
MIN_GREEN_THROUGH = 20      # Minimum green time for through phases (s)
MIN_GREEN_LEFT = 15         # Minimum green time for left-turn phases (s)
YELLOW_TIME = 3             # Yellow time per phase (s)
ALL_RED_TIME = 1            # All-red time per phase (s)

# EVOLVE-BLOCK-START
import numpy as np

def signal_timing_algorithm(traffic_flows):
    """
    Compute fixed-time signal timing.
    Fixed phase sequence: [NS_through, NS_left, EW_through, EW_left]
    Lane layout is fixed as defined above.

    Args:
        traffic_flows (dict): Movement-specific demand in veh/h, e.g.
            {'N_through': 300, 'N_left':150, 'N_right':100, ...}

    Returns:
        dict: Timing plan (green_times) and metadata.
    """
    cycle_length_min, cycle_length_max = 60, 130  # Minimum and maximum cycle length
    sat_flow_through, sat_flow_left = 1800, 1400  # Saturation flow for through lanes (veh/h/lane)

    # 1. Compute lane-level flow ratios for each movement
    movement_flow_ratio = {}
    for d in ['N', 'S', 'E', 'W']:
        q_th = traffic_flows.get(f'{d}_through', 0)
        q_lf = traffic_flows.get(f'{d}_left', 0)

        effective_th_lanes = LANES_THROUGH + 0.9 * LANES_THROUGH_RIGHT
        movement_flow_ratio[f'{d}_through'] = q_th / (effective_th_lanes * sat_flow_through)
        movement_flow_ratio[f'{d}_left'] = q_lf / (LANES_LEFT * sat_flow_left)

    # 2. Determine the critical flow ratio for each phase
    critical_flow_ratio = {
        'NS_through': max(movement_flow_ratio['N_through'], movement_flow_ratio['S_through']),
        'NS_left':    max(movement_flow_ratio['N_left'],    movement_flow_ratio['S_left']),
        'EW_through': max(movement_flow_ratio['E_through'], movement_flow_ratio['W_through']),
        'EW_left':    max(movement_flow_ratio['E_left'],    movement_flow_ratio['W_left']),
    }

    # 3. Compute cycle length and total effective green time
    lost_time = 4 * (YELLOW_TIME + ALL_RED_TIME)
    total_critical_ratio = sum(critical_flow_ratio.values())
    C0 = (1.5 * lost_time + 5) / (1 - total_critical_ratio) if total_critical_ratio < 1 else cycle_length_max
    cycle_length = max(cycle_length_min, min(cycle_length_max, round(C0)))
    effective_green_time = cycle_length - lost_time

    # 4. Allocate green time to each phase (with minimum green constraints)
    theoretical_green = {}
    actual_green_time = {}
    for phase, y in critical_flow_ratio.items():
        min_g = MIN_GREEN_THROUGH if 'through' in phase else MIN_GREEN_LEFT
        if total_critical_ratio == 0:
            theoretical_green[phase] = min_g
            actual_green_time[phase] = min_g
        else:
            g = round(y / total_critical_ratio * effective_green_time)
            theoretical_green[phase] = g
            actual_green_time[phase] = max(min_g, g)

    # 5. Calculate actual green time proportions per phase
    total_actual_green = sum(actual_green_time.values())
    green_time_ratio = {
        phase: round(g / total_actual_green, 4)
        for phase, g in actual_green_time.items()
    }

    return {
        'green_times': actual_green_time,
        'metadata': {
            'lost_time': lost_time,
            'critical_flow_ratio': critical_flow_ratio,
            'green_time_ratio': green_time_ratio,
            'theoretical_cycle_length': round(C0, 4),
            'actual_cycle_length': cycle_length,
            'theoretical_green': theoretical_green,
            'actual_green': actual_green_time,
        }
    }
# EVOLVE-BLOCK-END


def run_signal_control(traffic_flows):
    timing_plan = signal_timing_algorithm(traffic_flows)
    return traffic_flows, timing_plan


if __name__ == "__main__":
    # Quick test
    sample = {
        'N_through': 800, 'N_left': 150, 'N_right': 30,
        'S_through': 650, 'S_left': 120, 'S_right': 50,
        'E_through': 650, 'E_left': 140, 'E_right': 40,
        'W_through': 720, 'W_left': 110, 'W_right': 40
    }
    traffic_flows, plan = run_signal_control(sample)
    print(plan)
