def webster_signal_timing(traffic_flows, lane_config, min_green_through=20, min_green_left=15, cycle_min=60, cycle_max=150, yellow_time=3, all_red_time=1):
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
        total_through_lanes = lanes_through + lanes_through_right
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


def signal_timing(traffic_flows, lane_config, min_green_through=20, min_green_left=15, yellow_time=3, all_red_time=1):
    """
    Compute a simple signal timing plan based on traffic flow ratios for a fixed four-phase intersection.
    The plan uses a fixed 100-second cycle length and allocates green time proportionally to traffic flows.
    Phase sequence: [NS_through, NS_left, EW_through, EW_left]
    Each phase transition includes 3s yellow and 1s all-red time.

    Args:
        traffic_flows (dict): Traffic volume for each movement (veh/h), e.g.
            {'N_through': 300, 'N_left':150, 'N_right':100, ...}
        lane_config (dict): Lane configuration, e.g.
            {'N_through_lanes':2, 'N_right_lanes':1, 'N_through_right_lanes':1, ...}
        min_green_through (int): Minimum green time for through phases (seconds), default 20
        min_green_left (int): Minimum green time for left-turn phases (seconds), default 15
        yellow_time (int): Yellow time per phase (seconds), default 3
        all_red_time (int): All-red time per phase (seconds), default 1

    Returns:
        dict: Timing plan including green times and related parameters
    """
    # Fixed cycle length
    CYCLE_LENGTH = 100
    
    # Calculate total flow for each phase
    phase_flows = {
        'NS_through': traffic_flows.get('N_through', 0) + traffic_flows.get('S_through', 0),
        'NS_left': traffic_flows.get('N_left', 0) + traffic_flows.get('S_left', 0),
        'EW_through': traffic_flows.get('E_through', 0) + traffic_flows.get('W_through', 0),
        'EW_left': traffic_flows.get('E_left', 0) + traffic_flows.get('W_left', 0)
    }
    
    # Calculate total flow and flow ratios
    total_flow = sum(phase_flows.values())
    flow_ratios = {phase: flow/total_flow if total_flow > 0 else 0.25 
                  for phase, flow in phase_flows.items()}
    
    # Calculate total lost time (yellow + all-red)
    total_lost_time = 4 * (yellow_time + all_red_time)
    
    # Calculate available green time
    available_green = CYCLE_LENGTH - total_lost_time
    
    # Allocate green time based on flow ratios
    green_times = {}
    for phase, ratio in flow_ratios.items():
        green_time = round(ratio * available_green)
        # Ensure minimum green time requirements
        min_green = min_green_through if 'through' in phase else min_green_left
        green_times[phase] = max(min_green, green_time)
    
    return {
        'green_times': green_times,
        'other': {
            'cycle_length': CYCLE_LENGTH,
            'lost_time': total_lost_time,
            'flow_ratios': flow_ratios,
            'phase_flows': phase_flows
        }
    }


if __name__ == '__main__':
    # Example input: includes shared through-right lanes
    traffic_data = {
        'N_through': 1800, 'N_left': 150, 'N_right': 100,
        'S_through': 650, 'S_left': 120, 'S_right': 80,
        'E_through': 650, 'E_left': 100, 'E_right': 90,
        'W_through': 720, 'W_left': 110, 'W_right': 70
    }

    lane_data = {
        'N_through_lanes': 2, 'N_right_lanes': 0, 'N_left_lanes': 1, 'N_through_right_lanes': 1,
        'S_through_lanes': 2, 'S_right_lanes': 0, 'S_left_lanes': 1, 'S_through_right_lanes': 1,
        'E_through_lanes': 2, 'E_right_lanes': 0, 'E_left_lanes': 1, 'E_through_right_lanes': 1,
        'W_through_lanes': 2, 'W_right_lanes': 0, 'W_left_lanes': 1, 'W_through_right_lanes': 1
    }

    # Compute timing plan (parameters can be customized)
    timing_plan = webster_signal_timing(traffic_data, lane_data)
    print('Webster signal timing method:')
    print(timing_plan)

    # 测试新函数
    traffic_data = {
        'N_through': 1800, 'N_left': 150, 'N_right': 100,
        'S_through': 650, 'S_left': 120, 'S_right': 80,
        'E_through': 650, 'E_left': 100, 'E_right': 90,
        'W_through': 720, 'W_left': 110, 'W_right': 70
    }

    lane_data = {
        'N_through_lanes': 2, 'N_right_lanes': 0, 'N_left_lanes': 1, 'N_through_right_lanes': 1,
        'S_through_lanes': 2, 'S_right_lanes': 0, 'S_left_lanes': 1, 'S_through_right_lanes': 1,
        'E_through_lanes': 2, 'E_right_lanes': 0, 'E_left_lanes': 1, 'E_through_right_lanes': 1,
        'W_through_lanes': 2, 'W_right_lanes': 0, 'W_left_lanes': 1, 'W_through_right_lanes': 1
    }

    # 计算配时方案
    timing_plan = signal_timing(traffic_data, lane_data)
    print("\nsimple signal timing method:")
    print(timing_plan)