import configparser
import os
import shutil
import sys

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)


def _ensure_sumo_home():
    """
    Set SUMO_HOME to the install root (folder that contains a tools/ subdir).
    traci and sumolib need this on all platforms.
    """
    h = (os.environ.get("SUMO_HOME") or "").strip()
    if h and os.path.isdir(os.path.join(h, "tools")):
        return h

    if sys.platform == "win32":
        candidates = []
        for k in ("ProgramFiles(x86)", "ProgramFiles", "LocalAppData"):
            b = os.environ.get(k)
            if b:
                candidates.append(os.path.join(b, "Eclipse", "Sumo"))
        candidates.append(r"C:\Program Files (x86)\Eclipse\Sumo")
    else:
        candidates = ["/usr/share/sumo", "/opt/sumo", "/usr/local/share/sumo"]

    for root in candidates:
        if root and os.path.isdir(os.path.join(root, "tools")):
            os.environ["SUMO_HOME"] = root
            return root

    w = shutil.which("sumo")
    if w and sys.platform == "win32":
        # e.g. .../Sumo/bin/sumo.exe -> install root is one level above bin
        parent = os.path.normpath(os.path.join(os.path.dirname(w), os.pardir))
        if os.path.isdir(os.path.join(parent, "tools")):
            os.environ["SUMO_HOME"] = parent
            return parent
    if w and sys.platform != "win32":
        parent = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(w)), os.pardir, os.pardir))
        if os.path.basename(parent) == "sumo" and os.path.isdir(os.path.join(parent, "tools")):
            os.environ["SUMO_HOME"] = parent
            return parent
        p2 = os.path.join(os.path.dirname(parent), "share", "sumo")
        if os.path.isdir(os.path.join(p2, "tools")):
            os.environ["SUMO_HOME"] = p2
            return p2
    return None


_sumo_home = _ensure_sumo_home()
if _sumo_home:
    _tools = os.path.join(_sumo_home, "tools")
    if _tools not in sys.path:
        sys.path.insert(0, _tools)

from sumolib import checkBinary
import traci
import time



from sumo_monitor import IntersectionMonitor
from Webster_fix_4phase import signal_timing
from flow_generator import FlowGenerator


# phase codes based on isolated_intersection.net.xml
PHASE_NS_GREEN = 0
PHASE_NS_YELLOW = 1
PHASE_NS_ALL_RED = 2

PHASE_NSL_GREEN = 3
PHASE_NSL_YELLOW = 4
PHASE_NSL_ALL_RED = 5

PHASE_EW_GREEN = 6
PHASE_EW_YELLOW = 7
PHASE_EW_ALL_RED = 8

PHASE_EWL_GREEN = 9
PHASE_EWL_YELLOW = 10
PHASE_EWL_ALL_RED = 11


def set_sumo(gui, sumocfg_file_name, max_steps):
    """
    Configure various parameters of SUMO
    """
    if not _ensure_sumo_home():
        sys.exit(
            "Set SUMO_HOME to your SUMO install root (folder that contains a 'tools' subfolder). "
            "Windows: e.g. C:\\Program Files (x86)\\Eclipse\\Sumo. Linux: e.g. /usr/share/sumo. "
            "Or install SUMO and ensure 'sumo' is on PATH. See project README."
        )

    # setting the cmd mode or the visual mode    
    if gui == False:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')

    # Get the directory of the current Python file
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the path: current_dir/Intersections/sumocfg_file_name
    sumocfg_path = os.path.join(current_dir, "Intersections", sumocfg_file_name)

    # setting the cmd command to run sumo at simulation time
    sumo_cmd = [sumoBinary, "-c", sumocfg_path, "--no-step-log", "true", "--waiting-time-memory", str(max_steps)]

    return sumo_cmd


def run_tsc(args, green_times):
    """
    Run a 4-phase traffic signal control simulation using SUMO.
    
    This function implements a fixed-time traffic signal controller that cycles through
    four main phases: [NS_through, NS_left, EW_through, EW_left]. 
    Each phase includes     green, yellow, and all-red intervals for safety.
    
    Args:
        args: Configuration object containing simulation parameters
            - gui: Boolean flag for GUI mode
            - sumo_cfg: SUMO configuration file name
            - max_steps: Maximum simulation steps
            - intersection_id: Traffic light ID
            - radius: Monitoring radius
        green_times: Dictionary containing green time durations for each phase
            - NS_through: North-South through traffic green time
            - NS_left: North-South left turn green time  
            - EW_through: East-West through traffic green time
            - EW_left: East-West left turn green time
    
    Returns:
        dict: Simulation results summary from the intersection monitor
    """
    # Initialize SUMO simulation
    sumo_cmd = set_sumo(args.gui, args.sumo_cfg, args.max_steps)
    traci.start(sumo_cmd)
    sumo_monitor = IntersectionMonitor(intersection_id=args.intersection_id, radius=args.radius)

    step = 0
    
    # Define phase sequence: each phase includes green -> yellow -> all_red
    phases = [
        (PHASE_NS_GREEN, green_times['NS_through']),      # North-South through traffic
        (PHASE_NS_YELLOW, 3),                             # Yellow clearance time
        (PHASE_NS_ALL_RED, 1),                            # All-red safety interval
        (PHASE_NSL_GREEN, green_times['NS_left']),        # North-South left turns
        (PHASE_NSL_YELLOW, 3),
        (PHASE_NSL_ALL_RED, 1),
        (PHASE_EW_GREEN, green_times['EW_through']),      # East-West through traffic
        (PHASE_EW_YELLOW, 3),
        (PHASE_EW_ALL_RED, 1),
        (PHASE_EWL_GREEN, green_times['EW_left']),        # East-West left turns
        (PHASE_EWL_YELLOW, 3),
        (PHASE_EWL_ALL_RED, 1)
    ]
    
    current_phase = 0      # Index of current phase in the sequence
    phase_timer = 0        # Countdown timer for current phase
    
    # Main simulation loop
    while traci.simulation.getMinExpectedNumber() > 0:
        # Update traffic signal phase when timer expires
        if phase_timer <= 0:
            phase, duration = phases[current_phase]
            traci.trafficlight.setPhase(args.intersection_id, phase)
            phase_timer = duration
            current_phase = (current_phase + 1) % len(phases)  # Cycle through phases
        
        # Advance simulation by one step
        traci.simulationStep()
        sumo_monitor.update(step)
        
        # Decrement phase timer and simulation step counter
        phase_timer -= 1
        step += 1

    # Get simulation results and clean up
    sim_res = sumo_monitor.summary()
    traci.close()

    return sim_res


def evaluate(timing_plan, traffic_data=None, lane_data=None, gui=False, max_steps=1800, seed=1, num_simulations=3):
    """
    Evaluate traffic signal control performance using a given timing plan.
    
    This function sets up a traffic simulation environment, generates traffic flows,
    and runs the simulation with the provided timing plan to evaluate intersection 
    performance metrics.
    
    Args:
        timing_plan (dict): Signal timing plan containing green times
            Format: {'green_times': dict, 'other': dict}
        traffic_data (dict): Traffic flow data for each approach direction
            Format: {'N_through': int, 'N_left': int, 'N_right': int, ...}
        lane_data (dict): Lane configuration for each approach direction
            Format: {'N_through_lanes': int, 'N_left_lanes': int, ...}
        
        gui (bool): Enable SUMO GUI visualization (default: False)
        max_steps (int): Maximum simulation steps (default: 3600)
        seed (int): Random seed for traffic generation (default: 1)
        num_simulations (int): Number of simulations to run for averaging results (default: 1)
    
    Returns:
        dict: Simulation results containing performance metrics
            - total_vehicles: Total number of vehicles processed
            - avg_waiting_time: Average waiting time per vehicle
            - avg_travel_time: Average travel time per vehicle
            - throughput: Number of vehicles that completed their journey
            - queue_length: Average queue length at intersection
    """
    # Create configuration object
    class Args:
        def __init__(self):
            self.gui = gui
            self.sumo_cfg = 'isolated_intersection.sumocfg'
            self.max_steps = max_steps
            self.intersection_id = 'TL'
            self.radius = 150

    args = Args()

    # Set default traffic data if not provided
    if traffic_data is None:
        traffic_data = {
            'N_through': 1800, 'N_left': 150, 'N_right': 100,
            'S_through': 650, 'S_left': 120, 'S_right': 80,
            'E_through': 650, 'E_left': 100, 'E_right': 90,
            'W_through': 720, 'W_left': 110, 'W_right': 70
        }

    # Set default lane configuration if not provided
    if lane_data is None:
        lane_data = {
            'N_through_lanes': 2, 'N_right_lanes': 0, 'N_left_lanes': 1, 'N_through_right_lanes': 1,
            'S_through_lanes': 2, 'S_right_lanes': 0, 'S_left_lanes': 1, 'S_through_right_lanes': 1,
            'E_through_lanes': 2, 'E_right_lanes': 0, 'E_left_lanes': 1, 'E_through_right_lanes': 1,
            'W_through_lanes': 2, 'W_right_lanes': 0, 'W_left_lanes': 1, 'W_through_right_lanes': 1
        }

    # Use provided timing plan or calculate default using Webster method
    if timing_plan is None:
        timing_plan = signal_timing(traffic_data, lane_data)
        print("Using default Webster signal timing plan:")
    else:
        print("Using provided signal timing plan:")
    print(timing_plan)

    # Run multiple simulations if requested
    if num_simulations > 1:
        print(f"\nRunning {num_simulations} simulations for averaging results...")
        all_results = []
        
        for sim_idx in range(num_simulations):
            # Set different seed for each simulation to ensure randomness
            current_seed = seed + sim_idx
            print(f"\n--- Simulation {sim_idx + 1}/{num_simulations} (seed: {current_seed}) ---")
            
            # Generate traffic flow file with current seed
            flow_generator = FlowGenerator(max_steps=args.max_steps, traffic_flows=traffic_data)
            flow_generator.set_seed(current_seed)
            flow_generator.generate_routefile()

            # Run traffic simulation
            sim_s_t = time.time()
            sim_results = run_tsc(args, timing_plan['green_times'])
            sim_time = time.time() - sim_s_t
            print(f'Simulation {sim_idx + 1} time: {sim_time:.2f}s')
            print(f'Simulation {sim_idx + 1} results:')
            print(sim_results)
            
            all_results.append(sim_results)
        
        # Calculate average results
        print(f"\n=== AVERAGE RESULTS FROM {num_simulations} SIMULATIONS ===")
        results = _calculate_average_results(all_results)
        print("Average simulation results:")
        print(results)
        
    else:
        # Single simulation (original behavior)
        print("\nStarting simulation...")
        
        # Generate traffic flow file
        flow_generator = FlowGenerator(max_steps=args.max_steps, traffic_flows=traffic_data)
        flow_generator.set_seed(seed)
        flow_generator.generate_routefile()

        # Run traffic simulation
        sim_s_t = time.time()
        results = run_tsc(args, timing_plan['green_times'])
        print('simulation time:', time.time() - sim_s_t)
        print("\nSimulation results:")
        print(results)
    
    return results


def _calculate_average_results(all_results):
    """
    Calculate average results from multiple simulation runs.
    
    Args:
        all_results (list): List of simulation result dictionaries
        
    Returns:
        dict: Average results with the same structure as individual results
    """
    if not all_results:
        return {}
    
    # Initialize average result structure
    avg_result = {
        'routes': {},
        'intersection': {}
    }
    
    # Get all route IDs from all results
    all_route_ids = set()
    for result in all_results:
        if 'routes' in result:
            all_route_ids.update(result['routes'].keys())
    
    # Calculate average for each route
    for route_id in all_route_ids:
        route_values = {
            'avg_waiting_time': [],
            'avg_delay': [],
            'avg_stops': [],
            'avg_speed': [],
            'avg_queue_length': [],
            'sample_count': []
        }
        
        # Collect values from all simulations
        for result in all_results:
            if 'routes' in result and route_id in result['routes']:
                route_data = result['routes'][route_id]
                for key in route_values.keys():
                    if key in route_data:
                        route_values[key].append(route_data[key])
        
        # Calculate averages
        avg_route_stats = {}
        for key, values in route_values.items():
            if values:
                if key == 'sample_count':
                    # Sum sample counts
                    avg_route_stats[key] = int(sum(values))
                else:
                    # Calculate average for other metrics
                    avg_route_stats[key] = round(sum(values) / len(values), 2)
            else:
                avg_route_stats[key] = 0.0
        
        avg_result['routes'][route_id] = avg_route_stats
    
    # Calculate average for intersection overall
    intersection_values = {
        'avg_waiting_time': [],
        'avg_delay': [],
        'avg_stops': [],
        'avg_speed': [],
        'avg_queue_length': [],
        'total_vehicles': []
    }
    
    # Collect intersection values from all simulations
    for result in all_results:
        if 'intersection' in result:
            intersection_data = result['intersection']
            for key in intersection_values.keys():
                if key in intersection_data:
                    intersection_values[key].append(intersection_data[key])
    
    # Calculate averages
    avg_intersection_stats = {}
    for key, values in intersection_values.items():
        if values:
            if key == 'total_vehicles':
                # Sum total vehicles
                avg_intersection_stats[key] = int(sum(values))
            else:
                # Calculate average for other metrics
                avg_intersection_stats[key] = round(sum(values) / len(values), 2)
        else:
            avg_intersection_stats[key] = 0.0
    
    avg_result['intersection'] = avg_intersection_stats
    
    return avg_result


if __name__ == '__main__':
    # Example usage of the evaluate function
    # Create a sample timing plan for testing
    sample_timing_plan = {
        'green_times': {
            'NS_through': 30,
            'NS_left': 15,
            'EW_through': 25,
            'EW_left': 15
        },
        'other': {
            'cycle_length': 100,
            'lost_time': 16,
            'flow_ratios': {
                'NS_through': 0.3,
                'NS_left': 0.15,
                'EW_through': 0.25,
                'EW_left': 0.15
            }
        }
    }
    
    # Test with the sample timing plan
    print("=== Single Simulation Test ===")
    results = evaluate(sample_timing_plan, num_simulations=1)
    
    print("\n" + "="*50)
    print("=== Multiple Simulations Test ===")
    # Test with multiple simulations for averaging
    results_avg = evaluate(sample_timing_plan, num_simulations=3)



