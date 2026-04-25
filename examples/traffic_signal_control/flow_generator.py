import numpy as np
import math

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class FlowGenerator:
    """
    用于生成SUMO仿真所需的车辆流量。
    根据输入的流量字典，每秒随机生成车辆，并输出为SUMO可用的XML文件。

    示例:
        traffic_flows = {
            'N_through': 400,  # 北向直行每小时400辆
            'N_left': 150,    # 北向左转每小时150辆
            'N_right': 100,   # 北向右转每小时100辆
            'S_through': 380, # 南向直行每小时380辆
            'S_left': 120,    # 南向左转每小时120辆
            'S_right': 80,    # 南向右转每小时80辆
            'E_through': 350, # 东向直行每小时350辆
            'E_left': 100,    # 东向左转每小时100辆
            'E_right': 90,    # 东向右转每小时90辆
            'W_through': 320, # 西向直行每小时320辆
            'W_left': 110,    # 西向左转每小时110辆
            'W_right': 70     # 西向右转每小时70辆
        }
    """

    def __init__(self, max_steps, traffic_flows):
        """
        初始化FlowGenerator类。

        参数:
            max_steps (int): 仿真的最大步数。
            traffic_flows (dict): 输入流量字典，格式为 {direction}_{movement}: flow_rate。
                direction: 'N', 'S', 'E', 'W'
                movement: 'through', 'left', 'right'
        """
        self._max_steps = max_steps
        self._traffic_flows = traffic_flows

    def set_seed(self, seed):
        np.random.seed(seed)  # 单独设置seed的函数

    def generate_routefile(self, duration=None):
        """
        生成车辆流量文件。

        参数:
            duration (int, optional): 生成流量的时长，默认为self._max_steps。

        输出:
            生成SUMO可用的XML文件，包含车辆ID、路线、出发时间等信息。
            打印总流量和各方向的流量统计信息。
        """
        if duration is None:
            duration = self._max_steps  # 默认生成self._max_steps时长的流量

        # 生成车辆
        car_counter = 9  # 车辆ID从9开始累加
        car_gen_steps = []
        car_routes = []

        for step in range(duration):
            for route, flow in self._traffic_flows.items():
                # 每秒随机生成车辆数量（0、1或2辆）
                flow_per_second = flow / 3600  # 每小时流量转换为每秒流量
                n_cars = np.random.poisson(flow_per_second)
                for _ in range(n_cars):
                    car_gen_steps.append(step)
                    car_routes.append(route)

        # Get the directory of the current Python file
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Construct the path: current_dir/Intersections/sumocfg_file_name
        route_f_path = os.path.join(current_dir, "Intersections", 'isolated_routes.rou.xml')

        # 输出到文件
        with open(route_f_path, "w") as routes_file:
            print("""<routes>
            <vType accel="1.0" decel="4.5" id="standard_car" length="5.0" minGap="2.5" maxSpeed="25" sigma="0.5" />

            <route id="N_through" edges="N2TL TL2S"/>
            <route id="N_left" edges="N2TL TL2E"/>
            <route id="N_right" edges="N2TL TL2W"/>
            <route id="S_through" edges="S2TL TL2N"/>
            <route id="S_left" edges="S2TL TL2W"/>
            <route id="S_right" edges="S2TL TL2E"/>
            <route id="E_through" edges="E2TL TL2W"/>
            <route id="E_left" edges="E2TL TL2S"/>
            <route id="E_right" edges="E2TL TL2N"/>
            <route id="W_through" edges="W2TL TL2E"/>
            <route id="W_left" edges="W2TL TL2N"/>
            <route id="W_right" edges="W2TL TL2S"/>""", file=routes_file)

            for step, route in zip(car_gen_steps, car_routes):
                print(f'    <vehicle id="{route}_{car_counter}" type="standard_car" route="{route}" depart="{step}" departLane="random" departSpeed="10" />', file=routes_file)
                car_counter += 1

            print("</routes>", file=routes_file)

        # 计算并打印流量统计信息
        total_flow = len(car_routes)
        route_flow = {}
        for route in self._traffic_flows.keys():
            route_flow[route] = car_routes.count(route)

        print("流量统计信息:")
        print(f"总流量: {total_flow}辆")
        # for route, flow in route_flow.items():
        #     print(f"{route}: {flow}辆")

if __name__ == '__main__':
    # 测试FlowGenerator类
    traffic_flows = {
        'N_through': 400,  # 北向直行每小时400辆
        'N_left': 150,  # 北向左转每小时150辆
        'N_right': 100,  # 北向右转每小时100辆
        'S_through': 380,  # 南向直行每小时380辆
        'S_left': 120,  # 南向左转每小时120辆
        'S_right': 80,  # 南向右转每小时80辆
        'E_through': 350,  # 东向直行每小时350辆
        'E_left': 100,  # 东向左转每小时100辆
        'E_right': 90,  # 东向右转每小时90辆
        'W_through': 320,  # 西向直行每小时320辆
        'W_left': 110,  # 西向左转每小时110辆
        'W_right': 70  # 西向右转每小时70辆
    }


    # traffic_flows = {
    #     'N_through': 1500,  # 北向直行每小时400辆
    #     'N_left': 350,    # 北向左转每小时150辆
    #     'N_right': 100,   # 北向右转每小时100辆
    #     'S_through': 850, # 南向直行每小时380辆
    #     'S_left': 250,    # 南向左转每小时120辆
    #     'S_right': 80,    # 南向右转每小时80辆
    #     'E_through': 650, # 东向直行每小时350辆
    #     'E_left': 100,    # 东向左转每小时100辆
    #     'E_right': 90,    # 东向右转每小时90辆
    #     'W_through': 820, # 西向直行每小时320辆
    #     'W_left': 400,    # 西向左转每小时110辆
    #     'W_right': 70     # 西向右转每小时70辆
    # }

    generator = FlowGenerator(max_steps=3600, traffic_flows=traffic_flows)
    generator.set_seed(1)  # 设置随机种子
    generator.generate_routefile()  # 生成流量文件并打印统计信息
