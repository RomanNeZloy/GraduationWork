import json
import logging
from collectors import (
    CPUCollector,
    MemoryCollector,
    DiskCollector,
    NetworkCollector,
    SystemCollector,
    DevicesCollector,
    GPUMonitor,
)

# Настройка логирования
logging.basicConfig(
    level=logging.CRITICAL,
    #level=logging.DEBUG,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',

    handlers=[
        logging.FileHandler('agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('Agent')

def collect_all_metrics() -> dict:
    """Собирает все метрики со всех коллекторов."""

    # Инициализация коллекторов
    collectors = {
        'system': SystemCollector(),
        'cpu': CPUCollector(),
        'memory': MemoryCollector(),
        'disk': DiskCollector(),
        'network': NetworkCollector(max_connections=50),
        'devices': DevicesCollector(),
    }
    gpu_monitor = GPUMonitor()

    metrics = {}
    for name, collector in collectors.items():
        logger.debug(f"Collecting {name}...")
        metrics[name] = collector.safe_get()

    # GPU отдельно (у него другой интерфейс)
    metrics['gpu'] = [gpu.to_dict() for gpu in gpu_monitor.get_gpus()]

    return metrics

def main():
    logger.info("Agent started")
    #Для зацикливания работы программы.
    #interval = 5
    try:
        metrics = collect_all_metrics()

        #print(json.dumps(metrics, indent=2, ensure_ascii=False))
        print(json.dumps(metrics, indent=2, ensure_ascii=False))

        #time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
    except Exception as e:
        logger.error(f"Main loop error: {e}", exc_info=True)
        #time.sleep(interval)
    logger.info("End program")
if __name__ == '__main__':
    main()