import requests
import time
import psutil
import statistics
import json
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:5000/api/v1"

class PerformanceTest:
    def __init__(self):
        self.session = requests.Session()
        self.process = psutil.Process()
        self.results = {}

    def measure_endpoint(self, endpoint, method='GET', data=None, num_requests=100):
        """Measure response time and memory usage for an endpoint"""
        response_times = []
        memory_usage = []
        
        for _ in range(num_requests):
            # measure memory before request
            mem_before = self.process.memory_info().rss / 1024 / 1024  # convert to mb
            
            start_time = time.time()
            
            if method == 'GET':
                response = self.session.get(f"{BASE_URL}/{endpoint}")
            else:
                response = self.session.post(f"{BASE_URL}/{endpoint}", json=data)
            
            end_time = time.time()
            
            mem_after = self.process.memory_info().rss / 1024 / 1024
            
            response_time = (end_time - start_time) * 1000  # Convert to ms
            memory_delta = mem_after - mem_before
            
            response_times.append(response_time)
            memory_usage.append(memory_delta)
            
            # small delay to prevent overwhelming the server
            time.sleep(0.1)
        
        return {
            'avg_response_time': statistics.mean(response_times),
            'max_response_time': max(response_times),
            'min_response_time': min(response_times),
            'std_dev_response': statistics.stdev(response_times),
            'avg_memory_delta': statistics.mean(memory_usage),
            'max_memory_delta': max(memory_usage)
        }

    def test_filter_pets_scenarios(self):
        """Test different filter scenarios"""
        filter_scenarios = [
            {
                "name": "basic_name_search",
                "data": {
                    "type": "name",
                    "value": "Max"
                }
            },
            {
                "name": "complex_filter",
                "data": {
                    "type": "breed",
                    "value": "Golden Retriever",
                    "gender": "Male",
                    "health_condition": "good",
                    "sterilisation_status": 1
                }
            },
            {
                "name": "health_only",
                "data": {
                    "health_condition": "good"
                }
            },
            {
                "name": "gender_sterilisation",
                "data": {
                    "gender": "Female",
                    "sterilisation_status": 1
                }
            }
        ]

        results = {}
        for scenario in filter_scenarios:
            print(f"\nTesting filter scenario: {scenario['name']}")
            results[scenario['name']] = self.measure_endpoint(
                'filterpets', 
                method='POST', 
                data=scenario['data'],
                num_requests=50 
            )
            
            print(f"\nResults for {scenario['name']}:")
            print(f"Average Response Time: {results[scenario['name']]['avg_response_time']:.2f} ms")
            print(f"Max Response Time: {results[scenario['name']]['max_response_time']:.2f} ms")
            print(f"Average Memory Delta: {results[scenario['name']]['avg_memory_delta']:.2f} MB")

        return results

def main():
    tester = PerformanceTest()
    results = tester.test_filter_pets_scenarios()
    
    # save results to JSON file
    with open('filter_performance_results.json', 'w') as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    main()