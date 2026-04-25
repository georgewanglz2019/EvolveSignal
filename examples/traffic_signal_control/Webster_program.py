# EVOLVE-BLOCK-START
"""Traffic signal control example for OpenEvolve"""
import numpy as np


def signal_timing_algorithm(traffic_flows, lane_config, min_green_through=20, min_green_left=15, cycle_min=60, cycle_max=120, yellow_time=3, all_red_time=1):
    """
    Compute the optimal Webster signal timing plan for a fixed four-phase intersection.
    Phase sequence: [NS_through, NS_left, EW_through, EW_left].
    Supporting shared through-right lanes (no through-left lanes).
    yellow_time and all_red_time are set to 3s and 1s by default.

    Args:
        traffic_flows (dict): Traffic volume for each movement (veh/h), e.g.
            {'N_through': 300, 'N_left':150, 'N_right':100, ...}
        lane_config (dict): Lane configuration, supporting shared through-right lanes, e.g.
            {'N_through_lanes':2, 'N_right_lanes':1, 'N_through_right_lanes':1, ...}
        min_green_through (int): Minimum green time for through phases (seconds), default 20
        min_green_left (int): Minimum green time for left-turn phases (seconds), default 15
        cycle_min (int): Minimum signal cycle length (seconds), default 60
        cycle_max (int): Maximum signal cycle length (seconds), default 150
        yellow_time (int): Yellow time per phase (seconds), default 3
        all_red_time (int): All-red time per phase (seconds), default 1

    Returns:
        dict: Timing plan including cycle length, green times for each phase, lost time, and critical flow ratios
    """

    SAT_FLOW_THROUGH = 1800  # Saturation flow for through/right lanes (veh/h/lane)
    SAT_FLOW_LEFT = 1400     # Saturation flow for exclusive left-turn lanes (veh/h/lane)
    flow_ratios = {}

    # Calculate flow ratios for each direction and movement
    for direction in ['N', 'S', 'E', 'W']:
        q_through = traffic_flows.get(f'{direction}_through', 0)
        q_left = traffic_flows.get(f'{direction}_left', 0)
        q_right = traffic_flows.get(f'{direction}_right', 0)

        lanes_through = lane_config.get(f'{direction}_through_lanes', 0)
        lanes_left = lane_config.get(f'{direction}_left_lanes', 0)
        lanes_right = lane_config.get(f'{direction}_right_lanes', 0)
        lanes_through_right = lane_config.get(f'{direction}_through_right_lanes', 0)

        # Through flow ratio: sum of exclusive through and shared through-right lanes
        total_through_lanes = lanes_through + lanes_through_right * 0.9
        if total_through_lanes > 0:
            flow_ratios[f'{direction}_through'] = q_through / (total_through_lanes * SAT_FLOW_THROUGH)
        # Left-turn flow ratio: only exclusive left-turn lanes
        if lanes_left > 0:
            flow_ratios[f'{direction}_left'] = q_left / (lanes_left * SAT_FLOW_LEFT)
        # Right-turn flow ratio: sum of exclusive right and shared through-right lanes
        total_right_lanes = lanes_right + lanes_through_right
        if total_right_lanes > 0:
            right_capacity = (lanes_right + lanes_through_right) * SAT_FLOW_THROUGH
            flow_ratios[f'{direction}_right'] = q_right / right_capacity

    # For each phase, use the maximum critical flow ratio among relevant movements
    phase_y = {
        'NS_through': max(flow_ratios.get('N_through', 0), flow_ratios.get('S_through', 0)),
        'NS_left': max(flow_ratios.get('N_left', 0), flow_ratios.get('S_left', 0)),
        'EW_through': max(flow_ratios.get('E_through', 0), flow_ratios.get('W_through', 0)),
        'EW_left': max(flow_ratios.get('E_left', 0), flow_ratios.get('W_left', 0))
    }

    # Total lost time per cycle: 4 phases, each with yellow and all-red
    L = 4 * (yellow_time + all_red_time)
    Y = sum(phase_y.values())  # Sum of critical flow ratios
    print('V/C : Sum of critical flow ratios = ', Y)

    # Compute optimal cycle length using Webster's formula
    C0 = (1.5 * L + 5) / (1 - Y) if Y < 1 else cycle_max
    C = max(cycle_min, min(cycle_max, round(C0)))
    effective_green = C - L  # Total effective green time in a cycle

    # Allocate green time to each phase proportional to its flow ratio
    green_times = {}
    for phase, y in phase_y.items():
        if Y > 0:
            min_green = min_green_through if 'through' in phase else min_green_left
            green_times[phase] = max(min_green, round((y / Y) * effective_green))

    return {
        'green_times': green_times,
        'other': {
            'lost_time': L,
            'flow_ratios': phase_y,
            'theoretical_cycle_length': round(C0, 4),  # Webster计算的理论周期长度
            'actual_cycle_length': C,  # 考虑最小最大周期限制后的实际周期长度
        }
    }

# EVOLVE-BLOCK-END


# This part remains fixed (not evolved)
def create_default_lane_config():
    """Create default lane configuration for a standard four-approach intersection"""
    return {
        'N_through_lanes': 2, 'N_right_lanes': 0, 'N_left_lanes': 1, 'N_through_right_lanes': 1,
        'S_through_lanes': 2, 'S_right_lanes': 0, 'S_left_lanes': 1, 'S_through_right_lanes': 1,
        'E_through_lanes': 2, 'E_right_lanes': 0, 'E_left_lanes': 1, 'E_through_right_lanes': 1,
        'W_through_lanes': 2, 'W_right_lanes': 0, 'W_left_lanes': 1, 'W_through_right_lanes': 1
    }


def run_signal_control(traffic_flows):
    """
    Main function to run the signal control algorithm.
    This function is called by the evaluator.

    Args:
        traffic_flows (dict): Traffic volume data for each movement

    Returns:
        tuple: (traffic_flows, lane_config, timing_plan) for simulation
    """
    # Create default lane configuration
    lane_config = create_default_lane_config()
    
    # Generate timing plan using the algorithm
    timing_plan = signal_timing_algorithm(traffic_flows, lane_config)
    
    # Return the data needed for simulation
    return traffic_flows, lane_config, timing_plan


if __name__ == "__main__":
    # Example usage
    # test_traffic = {
    #     'N_through': 1800, 'N_left': 150, 'N_right': 100,
    #     'S_through': 650, 'S_left': 120, 'S_right': 80,
    #     'E_through': 650, 'E_left': 100, 'E_right': 90,
    #     'W_through': 720, 'W_left': 110, 'W_right': 70
    # }

    traffic_scenarios = [
        # Scenario 1: Balanced traffic  # Y = 0.50 - moderate traffic
        {
            'N_through': 800, 'N_left': 150, 'N_right': 30,
            'S_through': 650, 'S_left': 120, 'S_right': 50,
            'E_through': 650, 'E_left': 140, 'E_right': 40,
            'W_through': 720, 'W_left': 110, 'W_right': 40
        },
        # Scenario 2: East-West heavy  # Y = 0.56 - moderate traffic
        {
            'N_through': 490, 'N_left': 120, 'N_right': 30,
            'S_through': 430, 'S_left': 110, 'S_right': 50,
            'E_through': 1000, 'E_left': 260, 'E_right': 40,
            'W_through': 850, 'W_left': 230, 'W_right': 40
        },
        # Scenario 3: North-South heavy traffic  # Y = 0.83, NS major road - heavy traffic
        {
            'N_through': 2300, 'N_left': 300, 'N_right': 30,
            'S_through': 2200, 'S_left': 280, 'S_right': 50,
            'E_through': 400, 'E_left': 110, 'E_right': 40,
            'W_through': 450, 'W_left': 120, 'W_right': 40
        },
        # Scenario 4: Heavy traffic (North-South through and East-West left heavy)  # Y = 0.88, NS major road - heavy traffic
        {
            'N_through': 2300, 'N_left': 150, 'N_right': 30,
            'S_through': 2200, 'S_left': 120, 'S_right': 50,
            'E_through': 400, 'E_left': 350, 'E_right': 40,
            'W_through': 450, 'W_left': 300, 'W_right': 40
        }
    ]
    
    traffic_data, lane_data, timing_plan = run_signal_control(traffic_scenarios[3])
    print("Traffic data:", traffic_data)
    print("Lane configuration:", lane_data)
    print("Timing plan:", timing_plan)