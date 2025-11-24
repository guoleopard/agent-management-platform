import requests
import json

def test_register_agent():
    url = 'http://127.0.0.1:5000/agents'
    data = {
        'name': 'TestAgent',
        'description': 'A test agent',
        'status': 'inactive'
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Register Agent - Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 201
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_get_agents():
    url = 'http://127.0.0.1:5000/agents'
    
    try:
        response = requests.get(url)
        print(f"\nGet Agents - Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_get_agent():
    url = 'http://127.0.0.1:5000/agents/1'
    
    try:
        response = requests.get(url)
        print(f"\nGet Agent - Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_update_agent():
    url = 'http://127.0.0.1:5000/agents/1'
    data = {
        'description': 'Updated test agent',
        'status': 'running'
    }
    
    try:
        response = requests.put(url, json=data)
        print(f"\nUpdate Agent - Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_start_agent():
    url = 'http://127.0.0.1:5000/agents/1/start'
    
    try:
        response = requests.post(url)
        print(f"\nStart Agent - Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_get_agent_logs():
    url = 'http://127.0.0.1:5000/agents/1/logs'
    
    try:
        response = requests.get(url)
        print(f"\nGet Agent Logs - Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("Testing Agent Management Platform API...")
    
    # 安装requests库（如果需要）
    try:
        import requests
    except ImportError:
        print("Installing requests library...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests
    
    # 运行测试
    tests = [
        test_register_agent,
        test_get_agents,
        test_get_agent,
        test_update_agent,
        test_start_agent,
        test_get_agent_logs
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # 输出结果
    print("\n" + "="*50)
    print(f"Tests passed: {sum(results)}/{len(results)}")
    if all(results):
        print("All tests passed!")
    else:
        print("Some tests failed.")

if __name__ == "__main__":
    main()
