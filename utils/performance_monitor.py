"""
성능 모니터링 유틸
CPU/RAM/GPU 사용률을 측정하고 통계를 계산합니다.
"""

import psutil
import time
import threading
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """성능 측정 결과"""
    cpu_percent_avg: float          # 평균 CPU 사용률 (%)
    cpu_percent_max: float          # 최대 CPU 사용률 (%)
    ram_mb_avg: float               # 평균 RAM 사용량 (MB)
    ram_mb_peak: float              # 피크 RAM 사용량 (MB)
    gpu_vram_mb_current: float      # 현재 GPU VRAM (MB)
    gpu_vram_mb_peak: float         # 피크 GPU VRAM (MB)
    gpu_percent: float              # GPU 유틸리티 (%)
    processing_time_sec: float      # 처리 시간 (초)
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'cpu_percent_avg': round(self.cpu_percent_avg, 2),
            'cpu_percent_max': round(self.cpu_percent_max, 2),
            'ram_mb_avg': round(self.ram_mb_avg, 2),
            'ram_mb_peak': round(self.ram_mb_peak, 2),
            'gpu_vram_mb_current': round(self.gpu_vram_mb_current, 2),
            'gpu_vram_mb_peak': round(self.gpu_vram_mb_peak, 2),
            'gpu_percent': round(self.gpu_percent, 2),
            'processing_time_sec': round(self.processing_time_sec, 2)
        }


class PerformanceMonitor:
    """성능 모니터링 클래스"""
    
    def __init__(self, sample_interval: float = 0.5, process_pid: Optional[int] = None):
        """
        Args:
            sample_interval: 샘플링 주기 (초)
            process_pid: 모니터링할 프로세스 PID (None이면 현재 프로세스)
        """
        self.sample_interval = sample_interval
        self.process = psutil.Process(process_pid)
        
        # 샘플 데이터
        self.cpu_samples = []
        self.ram_samples = []
        self.gpu_vram_samples = []
        
        # 모니터링 상태
        self._monitoring = False
        self._monitor_thread = None
        self._start_time = None
        self._end_time = None
        
        # GPU 정보
        self._gpu_available = self._check_gpu_availability()
    
    def _check_gpu_availability(self) -> bool:
        """GPU 사용 가능 여부 확인"""
        try:
            import pynvml
            pynvml.nvmlInit()
            self._gpu_device_count = pynvml.nvmlDeviceGetCount()
            return self._gpu_device_count > 0
        except Exception as e:
            logger.warning(f"GPU 초기화 실패: {e}")
            self._gpu_device_count = 0
            return False
    
    def _get_gpu_memory_info(self) -> dict:
        """GPU 메모리 정보 조회"""
        if not self._gpu_available:
            return {
                'vram_mb': 0,
                'percent': 0
            }
        
        try:
            import pynvml
            pynvml.nvmlInit()
            
            total_vram_mb = 0
            used_vram_mb = 0
            
            # 모든 GPU의 메모리 합계
            for i in range(self._gpu_device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_vram_mb += mem_info.total / (1024 * 1024)
                used_vram_mb += mem_info.used / (1024 * 1024)
            
            gpu_percent = (used_vram_mb / total_vram_mb * 100) if total_vram_mb > 0 else 0
            
            return {
                'vram_mb': used_vram_mb,
                'total_vram_mb': total_vram_mb,
                'percent': gpu_percent
            }
        except Exception as e:
            logger.warning(f"GPU 메모리 조회 실패: {e}")
            return {
                'vram_mb': 0,
                'total_vram_mb': 0,
                'percent': 0
            }
    
    def _monitoring_loop(self):
        """백그라운드 모니터링 루프"""
        while self._monitoring:
            try:
                # CPU 사용률
                cpu_percent = self.process.cpu_percent(interval=None)
                self.cpu_samples.append(cpu_percent)
                
                # RAM 사용량 (MB)
                mem_info = self.process.memory_info()
                ram_mb = mem_info.rss / (1024 * 1024)
                self.ram_samples.append(ram_mb)
                
                # GPU VRAM
                if self._gpu_available:
                    gpu_info = self._get_gpu_memory_info()
                    self.gpu_vram_samples.append(gpu_info['vram_mb'])
                
                time.sleep(self.sample_interval)
            except Exception as e:
                logger.error(f"모니터링 중 오류: {e}")
                break
    
    def start(self):
        """성능 모니터링 시작"""
        self._start_time = time.time()
        self._monitoring = True
        self.cpu_samples = []
        self.ram_samples = []
        self.gpu_vram_samples = []
        
        # 모니터링 스레드 시작
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.debug("성능 모니터링 시작")
    
    def stop(self) -> PerformanceMetrics:
        """성능 모니터링 종료 및 결과 반환"""
        self._end_time = time.time()
        self._monitoring = False
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
        
        processing_time = self._end_time - self._start_time
        
        # 통계 계산
        cpu_avg = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0
        cpu_max = max(self.cpu_samples) if self.cpu_samples else 0
        
        ram_avg = sum(self.ram_samples) / len(self.ram_samples) if self.ram_samples else 0
        ram_peak = max(self.ram_samples) if self.ram_samples else 0
        
        gpu_vram_current = self.gpu_vram_samples[-1] if self.gpu_vram_samples else 0
        gpu_vram_peak = max(self.gpu_vram_samples) if self.gpu_vram_samples else 0
        
        # GPU 유틸리티
        gpu_info = self._get_gpu_memory_info()
        gpu_percent = gpu_info['percent']
        
        metrics = PerformanceMetrics(
            cpu_percent_avg=cpu_avg,
            cpu_percent_max=cpu_max,
            ram_mb_avg=ram_avg,
            ram_mb_peak=ram_peak,
            gpu_vram_mb_current=gpu_vram_current,
            gpu_vram_mb_peak=gpu_vram_peak,
            gpu_percent=gpu_percent,
            processing_time_sec=processing_time
        )
        
        logger.debug(f"성능 모니터링 종료 (CPU avg: {cpu_avg:.2f}%, "
                    f"RAM peak: {ram_peak:.2f}MB, GPU VRAM peak: {gpu_vram_peak:.2f}MB)")
        
        return metrics
