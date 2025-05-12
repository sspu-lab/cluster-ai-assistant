from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import time
import requests
import psutil
import nvidia_smi
from server_config import INTERNAL_MACHINES  # 从配置文件导入

app = Flask(__name__)
CORS(app)

# 存储所有机器的状态数据 (包括 A, B, C)
machine_status = {}

# 内网机器 A、B 的 IP 地址（请替换为实际 IP）
# INTERNAL_MACHINES = {
#     "A": "http://192.168.85.80:5000",
#     "B": "http://192.168.1.102:5000"
# }


def format_size(bytes, unit='GB'):
    """格式化存储单位"""
    units = {'KB': 1e3, 'MB': 1e6, 'GB': 1e9, 'TB': 1e12}
    return round(bytes / units[unit], 2)


def get_gpu_status():
    """获取 GPU 资源使用情况"""
    try:
        nvidia_smi.nvmlInit()
    except Exception as e:
        print("nvidia_smi 初始化失败：", e)
        return []

    gpus = []
    try:
        device_count = nvidia_smi.nvmlDeviceGetCount()
        for i in range(device_count):
            try:
                handle = nvidia_smi.nvmlDeviceGetHandleByIndex(i)
                mem_info = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
                util_rate = nvidia_smi.nvmlDeviceGetUtilizationRates(handle)
                temp = nvidia_smi.nvmlDeviceGetTemperature(handle, nvidia_smi.NVML_TEMPERATURE_GPU)
                name = nvidia_smi.nvmlDeviceGetName(handle).decode('utf-8')

                gpus.append({
                    'id': i,
                    'name': name,
                    'memory_free': format_size(mem_info.free),
                    'memory_total': format_size(mem_info.total),
                    'usage_percent': round(mem_info.used / mem_info.total * 100, 2),
                    'utilization_gpu': util_rate.gpu,
                    'utilization_memory': util_rate.memory,
                    'temperature': temp
                })
            except Exception as e:
                print(f"获取 GPU {i} 状态失败：", e)
    except Exception as e:
        print("获取 GPU 数量失败：", e)

    nvidia_smi.nvmlShutdown()
    return gpus


def get_system_status():
    """获取系统资源使用情况"""
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    net = psutil.net_io_counters()

    return {
        'cpu_usage': cpu_usage,
        'cpu_cores': psutil.cpu_count(logical=False),
        'cpu_threads': psutil.cpu_count(logical=True),
        'memory_total': format_size(memory.total),
        'memory_used': format_size(memory.used),
        'memory_free': format_size(memory.free),
        'memory_percent': memory.percent,
        'disk_total': format_size(disk.total, 'TB'),
        'disk_used': format_size(disk.used, 'GB'),
        'disk_free': format_size(disk.free, 'GB'),
        'disk_percent': disk.percent,
        'net_sent': format_size(net.bytes_sent, 'MB'),
        'net_recv': format_size(net.bytes_recv, 'MB')
    }


def collect_local_status():
    """
    定时采集公网机器 C 自身的状态，并存储到 machine_status。
    """
    while True:
        try:
            data = {
                'machine': 'C',
                'system': get_system_status(),
                'gpu': get_gpu_status()
            }
            machine_status['C'] = data
        except Exception as e:
            print("采集 C 机器状态失败：", e)

        # 每隔 10 秒更新一次数据
        time.sleep(10)


def fetch_internal_status():
    """
    定时从 A、B 机器获取状态数据，并存储到 machine_status。
    """
    while True:
        for name, url in INTERNAL_MACHINES.items():
            try:
                response = requests.get(f"{url}/full_status", timeout=5)
                if response.status_code == 200:
                    machine_status[name] = response.json()
                    print(f"成功获取 {name} 的状态数据")
                else:
                    print(f"获取 {name} 的状态失败，状态码：{response.status_code}")
            except requests.RequestException as e:
                print(f"请求 {name} 失败：", e)

        # 每隔 10 秒获取一次数据
        time.sleep(10)


@app.route('/update_status', methods=['POST'])
def update_status():
    """
    允许 A 和 B 主动推送状态数据，C 机器会存储这些数据。
    """
    data = request.get_json()
    machine_name = data.get('machine')
    if machine_name:
        machine_status[machine_name] = data
        return jsonify({"message": "Status updated successfully"}), 200
    return jsonify({"error": "Invalid data"}), 400


@app.route('/full_status', methods=['GET'])
def full_status():
    """
    返回所有机器的状态数据，包括 C 本身和 A、B 发送的数据。
    """
    return jsonify(machine_status)


if __name__ == '__main__':
    # 启动采集 C 机器自身状态的线程
    threading.Thread(target=collect_local_status, daemon=True).start()
    # 启动获取 A、B 状态数据的线程
    threading.Thread(target=fetch_internal_status, daemon=True).start()

    # 运行 Web 服务器
    app.run(host='0.0.0.0', port=5000)
