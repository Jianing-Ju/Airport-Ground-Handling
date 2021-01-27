# customers: {customer id: time_window duration resource} time_window - (left, right)
# fleet: name num capacity speed
# distance between i and j (depot - 0): distance[i][j]
import copy
import matplotlib.pyplot as plt

class VRPTW:
    def __init__(self, customers = None, fleet = None, distance = None):
        self.customers = customers
        self.fleet = fleet
        self.distance = distance
        self.routes = []
        self.cust_begin_time = {}
        self.results = {}

    def load_customers(self, customers):
        self.customers = customers

    def load_fleet(self, fleet):
        self.fleet = fleet

    def load_distance(self, distance):
        self.distance = distance

    def routing(self):
        all_id = self.customers.keys()
        remaining_id = set(all_id)
        served_id = []
        while len(remaining_id) != 0:
            remaining_custs = {id: self.customers[id] for id in remaining_id}
            # New route
            route = []
            # Choose an initial customer to be inserted - having the earliest start time
            init_customer_id = min(remaining_custs, key = lambda id: self.customers[id].time_window[0])
            init_customer_info = self.customers[init_customer_id]
            init_customer = {
                    "id": init_customer_id,
                    "tw_earliest": init_customer_info.time_window[0],
                    "tw_latest": init_customer_info.time_window[1],
                    "duration": init_customer_info.duration,
                    "resource": init_customer_info.resource,
                    "vehicle_ready_time": 0,
                    "begin_time": init_customer_info.time_window[0],
                    "push_forward": 0
                    }
            route.append(init_customer)
            served_id.append(init_customer_id)

            while 1:
                feasible_routes = [] # tuple: (inserted customer, resultant route)
                # All possibilities to insert a customer in a position
                for id in all_id:
                    if id not in served_id:
                        # Create a customer
                        customer_info = self.customers[id]
                        customer = {
                                "id": id,
                                "tw_earliest": customer_info.time_window[0],
                                "tw_latest": customer_info.time_window[1],
                                "duration": customer_info.duration,
                                "resource": customer_info.resource,
                                "vehicle_ready_time": None,
                                "begin_time": None,
                                "push_forward": 0
                                }
                        for insert_pos in range(len(route) + 1):
                            feasible = True
                            route_candidate = self.__insert_cust(route, insert_pos, customer)
                            # Update times of the subsequent customers after the inserted customer (included)
                            for i in range(insert_pos, len(route_candidate)):
                                self.__update_time(route_candidate, i)
                            #     # Check feasibility: begin_time < latest_start_time
                            #     if route_candidate[i]["begin_time"] > route_candidate[i]["tw_latest"]:
                            #         feasible = False
                            #         break
                            #     # If push forward becomes 0, all subsequent customers are feasible
                            #     if i != insert_pos and route_candidate[i]["push_forward"] == 0:
                            #         feasible = True
                            #         break
                            # if feasible:
                            #     feasible_routes.append((insert_pos, copy.deepcopy(route_candidate)))

                            if self.__route_feasible(route_candidate):
                                feasible_routes.append((insert_pos, copy.deepcopy(route_candidate)))

                if feasible_routes != []:
                    # From feasible routes, choose the one with minimum cost function
                    chosen = min(feasible_routes, key = lambda x: self.__cost_function(x))
                    insert_pos = chosen[0]
                    route = copy.deepcopy(chosen[1])
                    served_id.append(route[insert_pos]["id"])
                else:
                    # No feasible customers can be inserted
                    break

            # End of the route
            self.__check_feasible(route)

            self.routes.append(route)
            for cust in route:
                added_cust_id = cust["id"]
                added_cust_begin_time = cust["begin_time"]
                self.cust_begin_time[added_cust_id] = int(round(added_cust_begin_time))

            remaining_id = set(all_id).symmetric_difference(set(served_id))
        # End of all routes

        self.__present_results()




    def __insert_cust(self, route, index, customer):
        new_route = copy.deepcopy(route)
        new_route.insert(index, customer)

        return new_route

    def __update_time(self, route, i):

        if i == 0:
            route[i]["vehicle_ready_time"] = 0
        else:
            route[i]["vehicle_ready_time"] = route[i - 1]["begin_time"]\
                    + route[i-1]["duration"]\
                    + self.distance[route[i-1]["id"]][route[i]["id"]] / self.fleet.speed

        new_begin_time = max(route[i]["vehicle_ready_time"], route[i]["tw_earliest"])
        if route[i]["begin_time"] != None:
            route[i]["push_forward"] = max(0, new_begin_time - route[i]["begin_time"])
        route[i]["begin_time"] = new_begin_time

    def __cost_function(self, route_tuple):
        # Parameters for I3 from 2016 paper
        alpha_1 = 0.49
        alpha_2 = 0.49
        alpha_3 = 0.02
        miu = 1

        insert_pos = route_tuple[0]
        route = route_tuple[1]
        if insert_pos == 0:
            prev_id = 0
        else:
            prev_id = route[insert_pos - 1]['id']
        id = route[insert_pos]["id"]
        if insert_pos == len(route) - 1:
            next_id = 0
        else:
            next_id = route[insert_pos + 1]['id']

        c_1 = self.distance[prev_id][id] + self.distance[id][next_id] - miu * self.distance[prev_id][next_id]
        if insert_pos == len(route) - 1:
            c_2 = 0
        else:
            c_2 = route[insert_pos + 1]["push_forward"]

        c_3 = route[insert_pos]["tw_latest"] - route[insert_pos]["begin_time"]

        return alpha_1 * c_1 + alpha_2 * c_2 + alpha_3 * c_3

    def __route_feasible(self, route):
        resource = 0
        for cust in route:
            if cust["begin_time"] > cust["tw_latest"]:
                return False
            # Resource cannot exceed capacity of the vehicle
            resource += cust["resource"]
            if resource > self.fleet.capacity:
                return False

        return True

    def __present_results(self):
        # self.__print_routes()
        self.results["no_of_vehicle"] = len(self.routes)
        self.results["routes_with_customers"] = self.__cal_route_w_cust()
        self.results["route_distances"] = self.__cal_route_distances()
        self.results["total_distance"] = sum(self.results["route_distances"])

    def __cal_route_distances(self):
        route_distances = []
        total_distance = []
        for route in self.routes:
            route_distance = sum([self.distance[route[i]['id']][route[i+1]['id']]
                    for i in range(len(route)-1)])
            # plus depot to 1st customer and last castomer to depot
            route_distance += self.distance[0][route[0]['id']]
            route_distance += self.distance[route[-1]['id']][0]
            route_distances.append(route_distance)
        return route_distances

    def __print_routes(self):
        count = 1
        for route in self.routes:
            print("+++Route {}+++".format(count))
            count += 1
            for cust in route:
                print("Customer {}: {}".format(cust['id'], cust['begin_time']))

    def __cal_route_w_cust(self):
        routes_with_customers = []
        for route in self.routes:
            route_with_customers = [(cust['id'], cust['begin_time']) for cust in route]
            routes_with_customers.append(route_with_customers)
        return routes_with_customers

    def plot_routes(self):
        no_of_vehicle = self.results["no_of_vehicle"]
        # Generate y coordinates for routes:
        y_list = [1/(no_of_vehicle + 1) * (i+1) for i in range(no_of_vehicle)]
        labels = ["vehicle {}".format(i+1) for i in range(no_of_vehicle)]
        # Plot intervals:
        count = 0
        for route in self.routes:
            y = y_list[count]
            count += 1
            for cust in route:
                self.__plot_line(y, cust['begin_time'], cust['begin_time'] + cust['duration'])
        plt.yticks(y_list, labels)
        plt.ylim(0,1)
        plt.show()

    def __plot_line(self, y, x_start, x_stop):
        plt.hlines(y, x_start, x_stop, lw = 10)
        plt.vlines(x_start, y-0.02, y+0.02, lw = 2)
        plt.vlines(x_stop, y-0.02, y+0.02, lw = 2)

    def __check_feasible(self,route):
        resource = sum([cust['resource'] for cust in route])
        if resource > self.fleet.capacity:
            print("Capacity not feasible")
