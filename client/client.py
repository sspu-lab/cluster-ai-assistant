import requests
import json
import time
import psutil
import nvidia_smi
from client_config import SERVER_URL, MACHINE_NAME  # 从配置文件导入

# SERVER_URL = "http://192.168.10.212:5000/update_status"
# MACHINE_NAME = "A"  # 修改为唯一标识，如 A 或 B

def format_size(bytes, unit='GB'):
    units = {'KB': 1e3, 'MB': 1e6, 'GB': 1e9, 'TB': 1e12}
    return round(bytes / units[unit], 2)

def get_gpu_status():
    nvidia_smi.nvmlInit()
    device_count = nvidia_smi.nvmlDeviceGetCount()
    gpus = []

    for i in range(device_count):
        handle = nvidia_smi.nvmlDeviceGetHandleByIndex(i)
        mem_info = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
        util_rate = nvidia_smi.nvmlDeviceGetUtilizationRates(handle)
        temp = nvidia_smi.nvmlDeviceGetTemperature(handle, nvidia_smi.NVML_TEMPERATURE_GPU)

        name = nvidia_smi.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode('utf-8')

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

    nvidia_smi.nvmlShutdown()
    return gpus

def get_system_status():
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

def send_status():
    data = {
        'machine': MACHINE_NAME,
        'system': get_system_status(),
        'gpu': get_gpu_status()
    }
    try:
        response = requests.post(SERVER_URL, json=data)
        print(f"Response: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Failed to send data: {e}")

while True:
    send_status()
    time.sleep(10)  # 每 10 秒发送一次
