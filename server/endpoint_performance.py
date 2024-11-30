import requests
import time
import psutil
import statistics
import json

BASE_URL = "http://localhost:5000/api/v1"

class EndpointPerformanceTest:
    def __init__(self):
        self.session = requests.Session()
        self.process = psutil.Process()
        
    def measure_endpoint(self, endpoint, method='GET', data=None, num_requests=50):
        """Measure performance metrics for an endpoint"""
        response_times = []
        memory_usage = []
        errors = 0
        
        for _ in range(num_requests):
            try:
                # memory before request
                mem_before = self.process.memory_info().rss / 1024 / 1024  # MB
                
                # time the request
                start_time = time.time()
                if method == 'GET':
                    response = self.session.get(f"{BASE_URL}/{endpoint}")
                else:
                    response = self.session.post(f"{BASE_URL}/{endpoint}", json=data)
                end_time = time.time()
                
                # check if request was successful
                response.raise_for_status()
                
                # memory after request
                mem_after = self.process.memory_info().rss / 1024 / 1024  # MB
                
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                memory_delta = mem_after - mem_before
                
                response_times.append(response_time)
                memory_usage.append(memory_delta)
                
            except requests.exceptions.RequestException:
                errors += 1
            
            time.sleep(0.1)  # prevents for overwhelming the server
        
        # calculate metrics only if we have successful requests
        if response_times:
            return {
                'avg_response_time': statistics.mean(response_times),
                'max_response_time': max(response_times),
                'min_response_time': min(response_times),
                'std_dev_response': statistics.stdev(response_times),
                'avg_memory_usage': statistics.mean(memory_usage),
                'max_memory_usage': max(memory_usage),
                'error_rate': (errors / num_requests) * 100
            }
        else:
            return {
                'error': 'All requests failed',
                'error_rate': 100.0
            }

    def run_performance_tests(self):
        """Run performance tests for core endpoints"""
        # define endpoints to test
        endpoints = {
            'get_all_pets': {
                'path': 'getPets',
                'method': 'GET'
            },
            'get_top3_pets': {
                'path': 'getTop3',
                'method': 'GET'
            },
            'admin_get_users': {
                'path': 'admin/getUsers',
                'method': 'POST',
                'data': {'user_id': 1}
            },
            'admin_get_applications': {
                'path': 'admin/getApplications',
                'method': 'POST',
                'data': {'admin_id': 1}
            },
            'admin_get_adoptions': {
                'path': 'admin/getAdoptions',
                'method': 'POST',
                'data': {'user_id': 1}
            }
        }
        
        results = {}
        print("\nStarting Performance Tests...")
        print("=" * 50)
        
        for name, config in endpoints.items():
            print(f"\nTesting endpoint: {name}")
            results[name] = self.measure_endpoint(
                config['path'],
                method=config['method'],
                data=config.get('data'),
                num_requests=50
            )
            
            print(f"Results for {name}:")
            if 'error' in results[name]:
                print(f"  Error: {results[name]['error']}")
            else:
                print(f"  Average Response Time: {results[name]['avg_response_time']:.2f} ms")
                print(f"  Maximum Response Time: {results[name]['max_response_time']:.2f} ms")
                print(f"  Minimum Response Time: {results[name]['min_response_time']:.2f} ms")
                print(f"  Average Memory Usage: {results[name]['avg_memory_usage']:.2f} MB")
                print(f"  Error Rate: {results[name]['error_rate']:.2f}%")
            print("-" * 50)
        
        return results

def main():
    try:
        tester = EndpointPerformanceTest()
        results = tester.run_performance_tests()
        
        with open('endpoint_performance_results.json', 'w') as f:
            json.dump(results, f, indent=4)
        
        print("\nTesting completed. Results have been saved to 'endpoint_performance_results.json'")
        
    except Exception as e:
        print(f"An error occurred during testing: {str(e)}")

if __name__ == "__main__":
    main()