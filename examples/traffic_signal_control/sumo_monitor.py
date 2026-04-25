import traci
import numpy as np
from collections import defaultdict


class IntersectionMonitor:
    """
    Intersection monitoring class: Collects and analyzes traffic metrics for each route and the entire intersection.
    Metrics include: average cumulative waiting time, average delay, average number of stops, and queue length.
    
    Reference: 
    - https://sumo.dlr.de/docs/TraCI/Interfacing_TraCI_from_Python.html#subscriptions
    - https://github.com/eilifm/traci/blob/master/traci/constants.py
    
    Stop criterion: speed <= 0.1 m/s
    
    Usage:
        monitor = IntersectionMonitor('TL')
        for step in range(steps):
            traci.simulationStep()
            monitor.update(step)
        monitor.summary()
    """

    def __init__(self, intersection_id, radius=150, stop_speed=0.1, ideal_speed=13.89):
        """
        Initialize the intersection monitor.
        
        Args:
            intersection_id (str): ID of the intersection to monitor
            radius (float): Detection radius around the intersection (meters)
            stop_speed (float): Speed threshold to consider a vehicle as stopped (m/s)
            ideal_speed (float): Ideal speed for calculating delay (m/s)
        """
        self.intersection_id = intersection_id
        self.radius = radius
        self.stop_speed = stop_speed
        self.ideal_speed = ideal_speed
        self.ideal_time = self.radius / self.ideal_speed

        self.vehicles_passed_intersection = set()  # Set of vehicles that have passed the intersection
        self.vehicle_records = dict()  # Records for each vehicle's journey
        # route_id -> list of dict: {'veh_id', 'waiting', 'delay', 'stops', 'avg_speed'}
        self.route_stats = defaultdict(list)
        # Queue length statistics
        self.queue_lengths = []  # Queue length records per second
        self.route_queue_lengths = defaultdict(list)  # Queue length records per route per second

        # Subscribe to vehicle data within the intersection area
        traci.junction.subscribeContext(
            self.intersection_id,
            traci.constants.CMD_GET_VEHICLE_VARIABLE,
            self.radius,
            [
                traci.constants.VAR_LANEPOSITION,
                traci.constants.VAR_ROUTE_ID,
                traci.constants.VAR_SPEED,
                traci.constants.VAR_LANE_ID,
                traci.constants.VAR_EDGES,
                traci.constants.VAR_ACCUMULATED_WAITING_TIME
            ]
        )

    def update(self, current_time):
        """
        Update monitoring data for the current simulation step.
        
        Args:
            current_time (int): Current simulation time step
        """
        data = traci.junction.getContextSubscriptionResults(self.intersection_id)
        
        # Pre-calculate vehicle states to avoid repeated computations
        veh_status = {}
        for veh_id, veh_data in data.items():
            speed = veh_data.get(traci.constants.VAR_SPEED, 0)
            is_stopped = speed <= self.stop_speed
            has_passed = self._has_passed_intersection(veh_data)
            veh_status[veh_id] = {
                'is_stopped': is_stopped,
                'has_passed': has_passed,
                'route_id': veh_data.get(traci.constants.VAR_ROUTE_ID, None)
            }
        
        # Calculate queue length for each route
        route_queues = defaultdict(int)
        for veh_id, status in veh_status.items():
            if status['is_stopped'] and not status['has_passed']:
                route_id = status['route_id']
                if route_id:
                    route_queues[route_id] += 1
        
        # Update queue length records
        for route_id, queue_length in route_queues.items():
            self.route_queue_lengths[route_id].append(queue_length)
        
        # Update total queue length
        current_queue_length = sum(route_queues.values())
        self.queue_lengths.append(current_queue_length)

        # Update vehicle records
        for veh_id, veh_data in data.items():
            status = veh_status[veh_id]
            # Skip vehicles that have passed the intersection
            if status['has_passed']:
                self.vehicles_passed_intersection.add(veh_id)
                continue

            route_id = status['route_id']
            speed = veh_data.get(traci.constants.VAR_SPEED, 0)
            acc_wait = veh_data.get(traci.constants.VAR_ACCUMULATED_WAITING_TIME, 0)
            if veh_id not in self.vehicle_records:
                self.vehicle_records[veh_id] = {
                    'veh_id': veh_id,
                    'route_id': route_id,
                    'accum_waiting_time': acc_wait,
                    'stops': 0,
                    'last_speed': speed,
                    'enter_time': current_time
                }
            rec = self.vehicle_records[veh_id]
            rec['accum_waiting_time'] = acc_wait
            if rec['last_speed'] > self.stop_speed and speed <= self.stop_speed:
                rec['stops'] += 1
            rec['last_speed'] = speed
            rec['last_time'] = current_time

        # Process vehicles that have passed the intersection
        for veh_id in list(self.vehicle_records.keys()):
            if veh_id in self.vehicles_passed_intersection:
                rec = self.vehicle_records[veh_id]
                leave_time = rec.get('last_time', current_time)
                travel_time = leave_time - rec['enter_time']
                delay = travel_time - self.ideal_time
                # Calculate average speed: detection radius divided by travel time
                avg_speed = self.radius / travel_time if travel_time > 0 else 0
                self.route_stats[rec['route_id']].append({
                    'veh_id': veh_id,
                    'waiting': rec['accum_waiting_time'],
                    'delay': delay,
                    'stops': rec['stops'],
                    'avg_speed': avg_speed
                })
                del self.vehicle_records[veh_id]

    def _has_passed_intersection(self, veh_data):
        """
        Check if a vehicle has passed the intersection.
        
        Args:
            veh_data (dict): Vehicle data from TraCI
            
        Returns:
            bool: True if the vehicle is on the second edge, False otherwise
        """
        edges = veh_data.get(traci.constants.VAR_EDGES, ())
        lane_id = veh_data.get(traci.constants.VAR_LANE_ID, '')
        return len(edges) >= 2 and lane_id.startswith(edges[1])

    def summary(self):
        """
        Generate and print a summary of intersection performance metrics.
        
        Returns:
            dict: Summary statistics for each route and the entire intersection
        """
        result = {
            'routes': {},
            'intersection': {}
        }
        
        all_wait, all_delay, all_stops, all_speed, all_count = 0, 0, 0, 0, 0
        for route_id, stats in self.route_stats.items():
            waits = [x['waiting'] for x in stats]
            delays = [x['delay'] for x in stats]
            stops = [x['stops'] for x in stats]
            speeds = [x['avg_speed'] for x in stats]
            n = len(stats)
            if n == 0:
                continue
                
            route_stats = {
                'avg_waiting_time': round(np.mean(waits), 2),
                'avg_delay': round(np.mean(delays), 2),
                'avg_stops': round(np.mean(stops), 2),
                'avg_speed': round(np.mean(speeds), 2),
                'avg_queue_length': round(np.mean(self.route_queue_lengths[route_id]), 2) if route_id in self.route_queue_lengths else 0.0,
                'sample_count': int(n)
            }
            result['routes'][route_id] = route_stats
            
            all_wait += np.sum(waits)
            all_delay += np.sum(delays)
            all_stops += np.sum(stops)
            all_speed += np.sum(speeds)
            all_count += n

        # Calculate intersection-wide statistics
        if all_count > 0:
            result['intersection'] = {
                'avg_waiting_time': round(all_wait/all_count, 2),
                'avg_delay': round(all_delay/all_count, 2),
                'avg_stops': round(all_stops/all_count, 2),
                'avg_speed': round(all_speed/all_count, 2),
                'avg_queue_length': round(np.mean(self.queue_lengths), 2),
                'total_vehicles': int(all_count)
            }
        else:
            result['intersection'] = {
                'avg_waiting_time': 0.0,
                'avg_delay': 0.0,
                'avg_stops': 0.0,
                'avg_speed': 0.0,
                'avg_queue_length': 0.0,
                'total_vehicles': 0
            }

        # Print results
        for route_id, stats in result['routes'].items():
            print(f"Route {route_id}: Avg waiting time={stats['avg_waiting_time']:.2f}s, "
                  f"Avg delay={stats['avg_delay']:.2f}s, "
                  f"Avg stops={stats['avg_stops']:.2f}, "
                  f"Avg speed={stats['avg_speed']:.2f}m/s, "
                  f"Avg queue length={stats['avg_queue_length']:.2f}, "
                  f"Vehicle count={stats['sample_count']};")

        if all_count > 0:
            print(f"\nIntersection overall: Avg waiting time={result['intersection']['avg_waiting_time']:.2f}s, "
                  f"Avg delay={result['intersection']['avg_delay']:.2f}s, "
                  f"Avg stops={result['intersection']['avg_stops']:.2f}, "
                  f"Avg speed={result['intersection']['avg_speed']:.2f}m/s, "
                  f"Avg queue length={result['intersection']['avg_queue_length']:.2f}, "
                  f"Total vehicles={all_count}.")
        else:
            print("No vehicle data available!")

        return result


if __name__ == '__main__':
    # 测试代码
    import os
    import sys
    import time
    from sumo_controlller import set_sumo

    gui = False
    sumo_cmd = set_sumo(gui, 'isolated_intersection.sumocfg', 3600)
    traci.start(sumo_cmd)

    intersection_id = 'TL'
    monitor = IntersectionMonitor(intersection_id, radius=150)

    step = 0
    s_t = time.time()
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        monitor.update(step)
        step += 1
        # if step % 100 == 0:
        #     data = traci.junction.getContextSubscriptionResults(monitor.intersection_id)
            # print(data)
            # print()
            # info = monitor.summary()


    traci.close()

    end_t = time.time()
    print('time cost=', end_t - s_t, ' seconds')

    result = monitor.summary()

    print()
    print(result)

