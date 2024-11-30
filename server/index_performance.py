import requests
import time
import psutil
import statistics
import json

BASE_URL = "http://localhost:5000/api/v1"

class IndexPerformanceTest:
    def __init__(self):
        self.session = requests.Session()
        self.process = psutil.Process()

    def measure_query(self, query_data, num_requests=50):
        """Measure performance for a specific query"""
        response_times = []
        memory_usage = []
        
        for _ in range(num_requests):
            # Memory before request
            mem_before = self.process.memory_info().rss / 1024 / 1024  # MB
            
            # Time the request
            start_time = time.time()
            response = self.session.post(f"{BASE_URL}/filterpets", json=query_data)
            end_time = time.time()
            
            # Memory after request
            mem_after = self.process.memory_info().rss / 1024 / 1024  # MB
            
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            memory_delta = mem_after - mem_before
            
            if response.status_code == 200:
                response_times.append(response_time)
                memory_usage.append(memory_delta)
            
            time.sleep(0.1)  # Prevent overwhelming the server
        
        return {
            'avg_response_time': statistics.mean(response_times),
            'max_response_time': max(response_times),
            'min_response_time': min(response_times),
            'std_dev_response': statistics.stdev(response_times),
            'avg_memory_usage': statistics.mean(memory_usage),
            'max_memory_usage': max(memory_usage),
            'num_successful_requests': len(response_times)
        }

    def run_comparison_tests(self):
        # Test cases to compare indexed vs non-indexed fields
        test_cases = {
            'indexed_type': {
                'type': 'name',
                'value': 'Max'
            },
            'indexed_health': {
                'health_condition': 'good'
            },
            'indexed_sterilisation': {
                'sterilisation_status': '1'
            },
            'combined_indexed': {
                'type': 'name',
                'value': 'Max',
                'health_condition': 'good',
                'sterilisation_status': '1'
            },
            'non_indexed': {
                'gender': 'M'  # Example of a non-indexed field
            }
        }

        results = {}
        print("\nStarting Index Performance Comparison Tests...")
        print("=" * 60)

        for test_name, query_data in test_cases.items():
            print(f"\nTesting {test_name}...")
            results[test_name] = self.measure_query(query_data)
            
            print(f"Results for {test_name}:")
            print(f"  Average Response Time: {results[test_name]['avg_response_time']:.2f} ms")
            print(f"  Maximum Response Time: {results[test_name]['max_response_time']:.2f} ms")
            print(f"  Minimum Response Time: {results[test_name]['min_response_time']:.2f} ms")
            print(f"  Memory Usage: {results[test_name]['avg_memory_usage']:.2f} MB")
            print("-" * 60)

        # Calculate performance differences
        self.analyze_results(results)
        
        return results

    def analyze_results(self, results):
        """Analyze and display performance differences between indexed and non-indexed queries"""
        print("\nPerformance Analysis:")
        print("=" * 60)
        
        # Use non-indexed query as baseline
        baseline = results['non_indexed']['avg_response_time']
        
        for test_name, metrics in results.items():
            if test_name != 'non_indexed':
                improvement = ((baseline - metrics['avg_response_time']) / baseline) * 100
                print(f"\n{test_name} vs non-indexed:")
                print(f"  Performance improvement: {improvement:.2f}%")
                print(f"  Response time difference: {baseline - metrics['avg_response_time']:.2f} ms")
                print(f"  Memory usage difference: {metrics['avg_memory_usage'] - results['non_indexed']['avg_memory_usage']:.2f} MB")

def main():
    try:
        # Run the performance tests
        tester = IndexPerformanceTest()
        results = tester.run_comparison_tests()
        
        # Save detailed results to file
        with open('index_performance_results.json', 'w') as f:
            json.dump(results, f, indent=4)
        
        print("\nTesting completed. Detailed results saved to 'index_performance_results.json'")
        
    except Exception as e:
        print(f"An error occurred during testing: {str(e)}")

if __name__ == "__main__":
    main()