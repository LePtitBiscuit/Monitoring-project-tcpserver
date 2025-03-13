import psutil
import time

def get_process_usage():
    processes = []
    process_sorted = []
    # Première itération pour amorcer la collecte CPU
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            proc.cpu_percent(interval=None)  # Pré-collecte pour éviter 0%
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    time.sleep(1.5)  # Attendre 1 seconde pour une collecte plus précise

    # Seconde itération pour obtenir des valeurs correctes
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            info = proc.info
            memory_usage = info['memory_info'].rss / (1024 * 1024)  # Convertir en Mo
            processes.append({
                'pid': info['pid'],
                'name': info['name'],
                'cpu_percent': info['cpu_percent'],
                'memory_usage_mb': memory_usage
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    for proc in sorted(processes, key=lambda p: p['cpu_percent'], reverse=True):
        process_sorted.append(proc)
    return process_sorted

def display_process_usage():
    processes = get_process_usage()
    # print(processes)
    print(f"{'PID':<8}{'Nom du processus':<30}{'CPU (%)':<10}{'RAM (MB)':<10}")
    print("=" * 60)

    for proc in sorted(processes, key=lambda p: p['cpu_percent'], reverse=True):
        print(f"{proc['pid']:<8}{proc['name']:<30}{proc['cpu_percent']:<10.1f}{proc['memory_usage_mb']:<10.1f}")

if __name__ == "__main__":
    while True:
        display_process_usage()
        time.sleep(1)

