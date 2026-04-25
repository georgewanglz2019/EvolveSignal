"""
Evaluator for traffic signal control algorithms
"""

import importlib.util
import numpy as np
import time
import concurrent.futures
import traceback
import signal

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import traffic signal control modules
from sumo_controlller import evaluate as run_traffic_simulation
from flow_generator import FlowGenerator


def run_with_timeout(func, args=(), kwargs={}, timeout_seconds=300):
    """
    Run a function with a timeout using concurrent.futures

    Args:
        func: Function to run
        args: Arguments to pass to the function
        kwargs: Keyword arguments to pass to the function
        timeout_seconds: Timeout in seconds

    Returns:
        Result of the function or raises TimeoutError
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            result = future.result(timeout=timeout_seconds)
            return result
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Function timed out after {timeout_seconds} seconds")


def safe_float(value):
    """Convert a value to float safely"""
    try:
        return float(value)
    except (TypeError, ValueError):
        print(f"Warning: Could not convert {value} of type {type(value)} to float")
        return 0.0


def evaluate(program_path, traffic_scenarios=None):
    """
    Evaluate a traffic signal control program by running it on multiple traffic scenarios
    and measuring intersection performance metrics.

    Args:
        program_path: Path to the program file containing the signal control algorithm
        traffic_scenarios: List of traffic scenarios to test (optional)

    Returns:
        Dictionary of evaluation metrics
    """
    # Default traffic scenarios if none provided
    print('###########################################################')
    print('Evaluate start, program_path:', program_path)


    if traffic_scenarios is None:

        traffic_scenarios = [
            # Scenario 1: Balanced traffic across directions, critical_ratio_sum=0.868
            {
                'N_through': 1550, 'N_left': 210, 'N_right': 30,
                'S_through': 1450, 'S_left': 180, 'S_right': 50,
                'E_through': 1450, 'E_left': 200, 'E_right': 40,
                'W_through': 1400, 'W_left': 180, 'W_right': 40
            },
            # Scenario 2: Heavy traffic in North-South through and left, critical_ratio_sum=0.865
            {
                'N_through': 2600, 'N_left': 230, 'N_right': 30,
                'S_through': 2450, 'S_left': 250, 'S_right': 50,
                'E_through': 600, 'E_left': 80, 'E_right': 40,
                'W_through': 650, 'W_left': 90, 'W_right': 40
            },
            # Scenario 3: Heavy traffic in North-South through and East-West left, critical_ratio_sum=0.872
            {
                'N_through': 2500, 'N_left': 80, 'N_right': 60,
                'S_through': 2400, 'S_left': 90, 'S_right': 70,
                'E_through': 400, 'E_left': 330, 'E_right': 150,
                'W_through': 450, 'W_left': 340, 'W_right': 120
            }
        ]

    try:
        # Load the program
        spec = importlib.util.spec_from_file_location("program", program_path)
        program = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(program)

        # Check if the required function exists
        if not hasattr(program, "run_signal_control"):
            print(f"Error: program does not have 'run_signal_control' function")
            return {
                "delay_score": 0.0,
                "stops_score": 0.0,
                "combined_score": 0.0,
                "error": "Missing run_signal_control function",
            }

        # Run multiple trials for each scenario
        num_trials = 1
        all_results = []
        route_results = []  # 存储route级别的数据
        success_count = 0
        total_trials = len(traffic_scenarios) * num_trials

        for scenario_idx, traffic_data in enumerate(traffic_scenarios):
            for trial in range(num_trials):
                try:
                    start_time = time.time()

                    # Run the signal control algorithm with timeout
                    result = run_with_timeout(
                        program.run_signal_control, 
                        args=(traffic_data,),
                        timeout_seconds=60
                    )

                    # Handle different result formats
                    if isinstance(result, dict):
                        timing_plan = result
                        lane_data = None
                    elif isinstance(result, tuple) and len(result) == 2:
                        traffic_data, timing_plan = result
                        lane_data = None

                    elif isinstance(result, tuple) and len(result) == 3:
                        # (traffic_data, lane_data, timing_plan) format
                        traffic_data, lane_data, timing_plan = result

                    else:
                        print(f"Invalid result format")
                        continue

                    sim_results = run_traffic_simulation(
                        timing_plan=timing_plan,
                        traffic_data=traffic_data,
                        lane_data=lane_data,
                        gui=False,
                        max_steps=1800,
                        seed=trial + 1
                    )

                    end_time = time.time()

                    # Extract intersection-level metrics (only delay and stops)
                    intersection_metrics = sim_results.get('intersection', {})
                    
                    # Extract route-level metrics (only delay and stops)
                    # routes_metrics = sim_results.get('routes', {})
                    
                    # Ensure all intersection values are float (only delay and stops)
                    avg_delay = safe_float(intersection_metrics.get('avg_delay', 0))
                    avg_stops = safe_float(intersection_metrics.get('avg_stops', 0))

                    # Check if the intersection result is valid
                    if (np.isnan(avg_delay) or np.isnan(avg_stops) or
                        np.isinf(avg_delay) or np.isinf(avg_stops)):
                        print(f"Scenario {scenario_idx}, Trial {trial}: Invalid intersection result values")
                        continue

                    # Store intersection results (only delay and stops)
                    trial_result = {
                        'scenario': scenario_idx,
                        'trial': trial,
                        'avg_delay': avg_delay,
                        'avg_stops': avg_stops
                    }
                    all_results.append(trial_result)

                    
                    success_count += 1

                except TimeoutError as e:
                    print(f"Scenario {scenario_idx}, Trial {trial}: {str(e)}")
                    continue
                except Exception as e:
                    print(f"Scenario {scenario_idx}, Trial {trial}: Error - {str(e)}")
                    print(traceback.format_exc())
                    continue

        # If all trials failed, return zero scores
        if success_count == 0:
            return {
                "delay_score": 0.0,
                "stops_score": 0.0,
                "combined_score": 0.0,
                "error": "All trials failed",
            }

        # if any trails failed, return zero scores
        if success_count < len(traffic_scenarios):
            return {
                "delay_score": 0.0,
                "stops_score": 0.0,
                "combined_score": 0.0,
                "error": "Some trials failed.",
            }

        # Calculate aggregate intersection metrics (only delay and stops)
        delays = [r['avg_delay'] for r in all_results]
        stops = [r['avg_stops'] for r in all_results]

        avg_delay = float(np.mean(delays))
        avg_stops = float(np.mean(stops))

        # Convert to scores (higher is better)
        # Delay score: lower delay is better
        delay_score = float(1.0 / (1.0 + avg_delay / 100.0))
        
        # Stops score: lower stops is better
        stops_score = float(1.0 / (1.0 + avg_stops / 1.0))

        # Calculate combined score (equal weights for delay and stops)
        combined_score = float(
            0.5 * delay_score +
            0.5 * stops_score
        )


        print('###########################################################')
        print('Average metrics of all simulations, avg_delay=', avg_delay, 'avg_stops=', avg_stops)
        print('Evaluate Complete, delay_score=', delay_score, 'stops_score=', stops_score, 'combined_score=', combined_score)

        return {
            "delay_score": round(delay_score, 4),
            "stops_score": round(stops_score, 4),
            "combined_score": round(combined_score, 4),
            # "intersection_metrics": {
            #     "avg_delay": round(avg_delay, 2),
            #     "avg_stops": round(avg_stops, 2)
            # },
            # "route_metrics": route_summary
        }

    except Exception as e:
        print(f"Evaluation failed completely: {str(e)}")
        print(traceback.format_exc())
        return {
            "delay_score": 0.0,
            "stops_score": 0.0,
            "combined_score": 0.0,
            "error": str(e),
        }


if __name__ == '__main__':
    # Example usage
    test_program_path = "initial_program.py"   # 0.5398

    # test_program_path = "best_program.py"

    # test_program_path = "best_program2.py"

    # test_program_path = "best_program3.py"

    # test_program_path = "best_program4.py"

    # test_program_path = "Webster_program.py"      # avg_delay= 62.01 avg_stops= 1.16 combined_scor=0.5398
    #
    # test_program_path = "Webster_program_short.py"  # avg_delay= 62.01 avg_stops= 1.16 combined_scor=0.5398

    # test_program_path = 'best_program1-sangtiandao.py'  # avg_delay= 53.11 avg_stops= 0.65 combined_scor=0.629

    # test_program_path = 'best_program2-sangtiandao.py'  # avg_delay= 51.36 avg_stops= 0.74 combined_scor=0.618

    # test_program_path = "best_program5.py"    # avg_delay= 61.19 avg_stops= 1.13 combined_scor=0.5453



    if os.path.exists(test_program_path):
        import time
        start = time.time()
        print('start time:', start)
        print("Running evaluation...")
        results = evaluate(test_program_path)
        print("Evaluation results:", results)
        end = time.time()
        print("Total time:", end - start)
    else:
        print(f"Test program {test_program_path} not found")
        print("Please ensure initial_program.py exists in the current directory") 