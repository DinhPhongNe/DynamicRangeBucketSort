from typing import List, Union, Optional, Tuple, Dict, Any, Callable, Generator
import numpy as np
import numpy.typing as npt
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import math
import psutil
import time
import warnings
from enum import Enum
import cProfile
import io
import pstats
from collections import deque
import heapq
from functools import partial, lru_cache
import logging
import sys
from contextlib import contextmanager
import pickle
import os
from datetime import datetime
import threading
import multiprocessing as mp
import random
from sklearn.cluster import MiniBatchKMeans
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from scipy.stats import skew, kurtosis, entropy
from lz4.frame import compress, decompress
import tensorflow as tf
import asyncio
import numba

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s - %(processName)s - %(threadName)s'
)
logger = logging.getLogger(__name__)


class SortStrategy(Enum):
    AUTO = "auto"
    PARALLEL = "parallel"
    MEMORY_EFFICIENT = "memory_efficient"
    HYBRID = "hybrid"
    ADAPTIVE = "adaptive"
    STREAM = "stream"
    BLOCK_SORT = "block_sort"
    BUCKET_SORT = "bucket_sort"
    RADIX_SORT = "radix_sort"
    COMPRESSION_SORT = "compression_sort"
    EXTERNAL_SORT = "external_sort"


class Algorithm(Enum):
    QUICKSORT = "quicksort"
    MERGESORT = "mergesort"
    HEAPSORT = "heapsort"
    TIMSORT = "timsort"
    INTROSORT = "introsort"
    RADIXSORT = "radixsort"
    EXTERNALMERGESORT = "externalmergesort"


@dataclass
class PerformanceMetrics:
    cpu_time: float = 0.0
    wall_time: float = 0.0
    memory_peak: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    thread_count: int = 0
    context_switches: int = 0
    io_operations: int = 0
    network_usage: float = 0.0
    disk_io: float = 0.0
    cache_efficiency: float = 0.0


class AdaptiveCache:
    def __init__(self, initial_size: int = 1000):
        self.cache = {}
        self.size = initial_size
        self.hits = 0
        self.misses = 0
        self._access_history = deque(maxlen=initial_size)
        self._resize_threshold = 0.8
        self.min_size = initial_size // 2

    def _should_resize(self) -> bool:
      if not self._access_history:
          return False
      hit_rate = self.hits / (self.hits + self.misses + 1)
      return hit_rate < self._resize_threshold or len(self._access_history) < self.min_size

    def resize(self):
        if self._should_resize():
          self.size = max(self.min_size, int(self.size * 1.5))
          self._access_history = deque(maxlen=self.size)

    @lru_cache(maxsize=256)
    def get(self, key: Union[int, str]) -> Any:
        if key in self.cache:
            self.hits += 1
            self._access_history.append(key)
            return self.cache[key]
        self.misses += 1
        self.resize()
        return None

    def put(self, key: Union[int, str], value: Any) -> None:
        if len(self.cache) >= self.size:
            oldest = self._access_history.popleft()
            self.cache.pop(oldest, None)
        self.cache[key] = value
        self._access_history.append(key)


class BlockManager:
    def __init__(self, block_size: int = 4096):
        self.block_size = block_size
        self.blocks = []

    def split_into_blocks(self, arr: npt.NDArray) -> List[npt.NDArray]:
        return np.array_split(arr, max(1, len(arr) // self.block_size))

    def merge_blocks(self, blocks: List[npt.NDArray]) -> npt.NDArray:
        if not blocks:
            return np.array([])

        result = np.zeros(sum(len(block) for block in blocks), dtype=blocks[0].dtype)
        pos = 0

        for block in blocks:
            result[pos:pos + len(block)] = block
            pos += len(block)

        return result


@dataclass
class SortStats:
    execution_time: float
    memory_usage: float
    items_processed: int
    cpu_usage: float
    bucket_distribution: List[int]
    strategy_used: str
    algorithm_used: str
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)
    stream_chunks: int = 0
    compression_ratio: float = 1.0
    error_detected: bool = False
    fallback_strategy: str = "None"


class CacheManager:
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        self._access_history = deque(maxlen=max_size)

    @lru_cache(maxsize=128)
    def get(self, key: Union[int, str]) -> Any:
        if key in self.cache:
            self.hits += 1
            self._access_history.append(key)
            return self.cache[key]
        self.misses += 1
        return None

    def put(self, key: Union[int, str], value: Any) -> None:
        if len(self.cache) >= self.max_size:
            oldest = self._access_history.popleft()
            self.cache.pop(oldest, None)
        self.cache[key] = value
        self._access_history.append(key)


class StreamProcessor:
    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
        self.buffer = deque(maxlen=chunk_size)
        self._lock = threading.Lock()
        self.chunks_processed = 0
        self.linear_model = LinearRegression()
        self.last_chunk_size = chunk_size
        self.chunk_history = deque(maxlen=5)

    def process_stream(self, data_stream: Generator) -> Generator:
        for item in data_stream:
            with self._lock:
                self.buffer.append(item)
                if len(self.buffer) >= self.chunk_size:
                    self.chunks_processed += 1
                    yield sorted(self.buffer)
                    self.chunk_history.append(len(self.buffer))
                    self.buffer.clear()
                    self._update_chunk_size()

        if self.buffer:
            self.chunks_processed += 1
            yield sorted(self.buffer)
            self.chunk_history.append(len(self.buffer))
            
    def _update_chunk_size(self):
      if len(self.chunk_history) < 2:
        return
        
      x = np.arange(1, len(self.chunk_history) + 1).reshape(-1, 1)
      y = np.array(self.chunk_history)
      self.linear_model.fit(x,y)
      next_chunk_size = self.linear_model.predict(np.array([[len(self.chunk_history) + 1]]))[0]
      self.chunk_size = max(1000, int(next_chunk_size))


class MetricsCollector:
    def __init__(self):
        self.metrics = []
        self.start_time = time.perf_counter()

    def record(self, metric_name: str, value: Any):
        self.metrics.append({
            'name': metric_name,
            'value': value,
            'timestamp': time.perf_counter() - self.start_time
        })

    def get_summary(self) -> Dict[str, Any]:
        return {
            'total_duration': time.perf_counter() - self.start_time,
            'metrics': self.metrics
        }


@contextmanager
def performance_tracker():
    start_time = time.perf_counter()
    start_cpu = time.process_time()

    try:
        yield
    finally:
        end_cpu = time.process_time()
        end_time = time.perf_counter()

        logger.debug(f"CPU Time: {end_cpu - start_cpu:.4f}s")
        logger.debug(f"Wall Time: {end_time - start_time:.4f}s")


class EnhancedHyperionSort:
    def __init__(
        self,
        strategy: SortStrategy = SortStrategy.AUTO,
        n_workers: Optional[int] = None,
        chunk_size: Optional[int] = None,
        profile: bool = False,
        cache_size: int = 2000,
        adaptive_threshold: float = 0.8,
        stream_mode: bool = False,
        block_size: int = 4096,
        use_ml_prediction: bool = True,
        compression_threshold: int = 10000,
        external_sort_threshold = 100000
    ):
        self.strategy = strategy
        self.profile = profile
        self.n_workers = n_workers or max(1, psutil.cpu_count() - 1)
        self.chunk_size = chunk_size
        self.cache = AdaptiveCache(cache_size)
        self.adaptive_threshold = adaptive_threshold
        self.stream_mode = stream_mode
        self.block_manager = BlockManager(block_size)
        self.metrics = MetricsCollector()
        self._setup_logging()
        self.start_time = time.perf_counter()
        self.stream_processor = StreamProcessor(chunk_size=self.chunk_size or 1000)
        self.use_ml_prediction = use_ml_prediction
        self.ml_model = self._train_ml_model() if use_ml_prediction else None
        self.compression_threshold = compression_threshold
        self.fallback_strategy = Algorithm.MERGESORT
        self.external_sort_threshold = external_sort_threshold
        self.buffer_size = 4096

    def _setup_metrics(self) -> Dict[str, Any]:
        return {
            'sort_times': [],
            'memory_usage': [],
            'cache_stats': {'hits': 0, 'misses': 0},
            'block_stats': {'splits': 0, 'merges': 0}
        }
    
    def _train_ml_model(self):
        np.random.seed(42)
        n_samples = 1000
        data = np.random.rand(n_samples, 6) # Adjusted to have 6 features
        labels = np.zeros(n_samples)
        for i in range(n_samples):
          if data[i,0] < 0.3:
             labels[i] = 1 #use bucket
          elif data[i, 1] > 0.7:
              labels[i] = 2 # use hybrid
          elif data[i, 2] > 0.6:
              labels[i] = 3 # use parallel
          elif data[i, 3] > 0.8:
               labels[i] = 4 #use radix
          elif data[i, 4] > 0.9:
               labels[i] = 5 # use compression
          else :
             labels[i] = 0 # use adaptive
        
        model = tf.keras.Sequential([
        tf.keras.layers.Dense(128, activation='relu', input_shape=(6,)),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(6)
        ])
        model.compile(optimizer='adam', loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True))

        model.fit(data, labels, epochs = 10, verbose=0)
        return model

    def _predict_strategy(self, arr: npt.NDArray) -> SortStrategy:
      if not self.ml_model:
          return self._choose_optimal_strategy(arr)
      
      n = len(arr)
      sample_size = min(1000, n)
      sample = arr[np.random.choice(n, sample_size, replace=False)]
      
      is_nearly_sorted = np.sum(np.diff(sample) < 0) < len(sample) * 0.1
      std_dev = np.std(sample)
      range_size = np.ptp(sample)
      data_skewness = skew(sample)
      data_kurtosis = kurtosis(sample)
      
      features = np.array([std_dev, range_size, is_nearly_sorted, len(arr), data_skewness, data_kurtosis]).reshape(1, -1)
      predicted_strategy = np.argmax(self.ml_model.predict(features, verbose = 0)[0])
      
      if predicted_strategy == 0:
         return SortStrategy.ADAPTIVE
      elif predicted_strategy == 1:
          return SortStrategy.BUCKET_SORT
      elif predicted_strategy == 2:
         return SortStrategy.HYBRID
      elif predicted_strategy == 3:
          return SortStrategy.PARALLEL
      elif predicted_strategy == 4:
          return SortStrategy.RADIX_SORT
      elif predicted_strategy == 5:
          return SortStrategy.COMPRESSION_SORT
      else:
        return SortStrategy.ADAPTIVE
    
    def _advanced_block_sort(self, arr: npt.NDArray) -> npt.NDArray:
        if len(arr) < 1000:
            return np.sort(arr)

        blocks = self.block_manager.split_into_blocks(arr)
        self.metrics.record('block_splits', 1)

        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            sorted_blocks = list(executor.map(self._optimize_block_sort, blocks))

        while len(sorted_blocks) > 1:
            new_blocks = []
            for i in range(0, len(sorted_blocks), 2):
                if i + 1 < len(sorted_blocks):
                    merged = self._merge_sorted_arrays(
                        [sorted_blocks[i], sorted_blocks[i + 1]])
                    new_blocks.append(merged)
                else:
                    new_blocks.append(sorted_blocks[i])
            sorted_blocks = new_blocks
            self.metrics.record('block_merges', 1)

        return sorted_blocks[0]

    def _optimize_block_sort(self, block: npt.NDArray) -> npt.NDArray:
        if len(block) < 16:
            return self._insertion_sort(block)

        std_dev = np.std(block)
        range_size = np.ptp(block)

        if std_dev < range_size / 100:
            return self._bucket_sort(block)
        elif len(block) < 1000:
            return self._quicksort(block)
        else:
            return self._introsort(block)
    
    def _radix_sort(self, arr: npt.NDArray) -> npt.NDArray:
        if len(arr) == 0:
            return arr
        
        max_val = np.max(arr)
        exp = 1
        
        while max_val // exp > 0:
            buckets = [[] for _ in range(10)]
            for x in arr:
                digit = (x // exp) % 10
                buckets[digit].append(x)
                
            arr = np.concatenate(buckets)
            exp *= 10
        return arr
    

    def _bucket_sort(self, arr: npt.NDArray) -> npt.NDArray:
        if len(arr) == 0:
            return arr

        n_buckets = self._optimize_bucket_count(arr)
        min_val, max_val = arr.min(), arr.max()

        if min_val == max_val:
            return arr

        buckets = [[] for _ in range(n_buckets)]
        width = (max_val - min_val) / n_buckets

        for x in arr:
            bucket_idx = int((x - min_val) / width)
            if bucket_idx == n_buckets:
                bucket_idx -= 1
            buckets[bucket_idx].append(x)

        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            sorted_buckets = list(executor.map(
                lambda x: sorted(x) if len(x) > 0 else [],
                buckets
            ))

        return np.concatenate([np.array(bucket) for bucket in sorted_buckets if bucket])

    def _quicksort(self, arr: npt.NDArray) -> npt.NDArray:
        if len(arr) <= 16:
            return self._insertion_sort(arr)

        pivot = self._ninther(arr)
        left = arr[arr < pivot]
        middle = arr[arr == pivot]
        right = arr[arr > pivot]

        if len(arr) > 1000:
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_left = executor.submit(self._quicksort, left)
                future_right = executor.submit(self._quicksort, right)
                sorted_left = future_left.result()
                sorted_right = future_right.result()
                return np.concatenate([sorted_left, middle, sorted_right])
        else:
            return np.concatenate([
                self._quicksort(left),
                middle,
                self._quicksort(right)
            ])

    def _introsort(self, arr: npt.NDArray, max_depth: Optional[int] = None) -> npt.NDArray:
        if max_depth is None:
            max_depth = 2 * int(math.log2(len(arr)))

        if len(arr) <= 16:
            return self._insertion_sort(arr)
        elif max_depth == 0:
            return self._heapsort(arr)
        else:
            pivot = self._ninther(arr)
            left = arr[arr < pivot]
            middle = arr[arr == pivot]
            right = arr[arr > pivot]

            if len(arr) > 1000:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    future_left = executor.submit(
                        self._introsort, left, max_depth - 1
                    )
                    future_right = executor.submit(
                        self._introsort, right, max_depth - 1
                    )
                    sorted_left = future_left.result()
                    sorted_right = future_right.result()
                    return np.concatenate([sorted_left, middle, sorted_right])
            else:
                return np.concatenate([
                    self._introsort(left, max_depth - 1),
                    middle,
                    self._introsort(right, max_depth - 1)
                ])

    def _ninther(self, arr: npt.NDArray) -> float:
        if len(arr) < 9:
            return np.median(arr)

        thirds = len(arr) // 3
        medians = [
            np.median([arr[i], arr[i + thirds], arr[i + 2 * thirds]])
            for i in range(3)
        ]
        return np.median(medians)
    
    @numba.jit(nopython = True)
    def _insertion_sort(self, arr: npt.NDArray) -> npt.NDArray:
        for i in range(1, len(arr)):
            key = arr[i]
            j = i - 1
            while j >= 0 and arr[j] > key:
                arr[j + 1] = arr[j]
                j -= 1
            arr[j + 1] = key
        return arr

    def _heapsort(self, arr: npt.NDArray) -> npt.NDArray:
        def heapify(n: int, i: int):
            largest = i
            left = 2 * i + 1
            right = 2 * i + 2

            if left < n and arr[left] > arr[largest]:
                largest = left

            if right < n and arr[right] > arr[largest]:
                largest = right

            if largest != i:
                arr[i], arr[largest] = arr[largest], arr[i]
                heapify(n, largest)

        n = len(arr)
        for i in range(n // 2 - 1, -1, -1):
            heapify(n, i)

        for i in range(n - 1, 0, -1):
            arr[0], arr[i] = arr[i], arr[0]
            heapify(i, 0)

        return arr

    def _stream_sort_and_collect(self, data_stream: Generator) -> Tuple[npt.NDArray, SortStats]:
        all_chunks = []
        for chunk in self.stream_processor.process_stream(data_stream):
            all_chunks.append(np.array(chunk))

        if not all_chunks:
            return np.array([]), self._calculate_stats(np.array([]), "stream", "none", stream_chunks=0)

        merged_array = np.concatenate(all_chunks)
        return merged_array, self._calculate_stats(merged_array, "stream", "timsort", stream_chunks=self.stream_processor.chunks_processed)
    
    def _compression_sort(self, arr: npt.NDArray) -> Tuple[npt.NDArray, float]:
        if len(arr) < self.compression_threshold:
           return arr, 1.0

        compressed_data = compress(arr.tobytes())
        compression_ratio = len(compressed_data) / arr.nbytes
        
        if compression_ratio > 1.0:
             return arr, 1.0
        
        decompressed_arr = np.frombuffer(decompress(compressed_data), dtype = arr.dtype)
        sorted_arr = np.sort(decompressed_arr)
        return sorted_arr, compression_ratio
    
    def _pivot_tree_partition(self, arr: npt.NDArray) -> List[npt.NDArray]:
        if len(arr) <= 100:
            return [arr]

        def _recursive_partition(arr, depth=0):
          if len(arr) <= 100 or depth > 10:
            return [arr]

          pivot = self._ninther(arr)
          left = arr[arr < pivot]
          middle = arr[arr == pivot]
          right = arr[arr > pivot]

          return _recursive_partition(left, depth+1) + [middle] + _recursive_partition(right, depth+1)
        
        partitions = _recursive_partition(arr)
        return [part for part in partitions if len(part) > 0]

    async def _read_chunk(self, file_path: str, offset: int, size: int) -> npt.NDArray:
      loop = asyncio.get_event_loop()
      return await loop.run_in_executor(None, partial(self._read_chunk_sync, file_path, offset, size))

    def _read_chunk_sync(self, file_path: str, offset: int, size: int) -> npt.NDArray:
      with open(file_path, 'rb') as file:
          file.seek(offset)
          data = file.read(size)
          return np.frombuffer(data, dtype = np.float64)

    async def _external_sort(self, arr: npt.NDArray) -> npt.NDArray:
      file_path = "temp_data.bin"
      arr.tofile(file_path)
      chunk_size = self.buffer_size
      num_chunks = math.ceil(len(arr) * arr.itemsize / chunk_size)

      sorted_chunks = []
      tasks = []
      for i in range(num_chunks):
          offset = i * chunk_size
          size = min(chunk_size, len(arr) * arr.itemsize - offset)
          task = self._read_chunk(file_path, offset, size)
          tasks.append(task)
        
      chunks = await asyncio.gather(*tasks)
      
      for chunk in chunks:
        sorted_chunks.append(np.sort(chunk))
      
      if len(sorted_chunks) == 0:
          return np.array([])
      
      result = self._merge_sorted_arrays(sorted_chunks)
      os.remove(file_path)
      return result

    def sort(
        self,
        arr: Union[List[float], npt.NDArray, Generator],
    ) -> Union[Tuple[npt.NDArray, SortStats], Generator]:
        self.start_time = time.perf_counter()
        self.logger.info("Starting sort operation...")
        original_arr = np.array(arr, dtype=np.float64) if isinstance(arr, list) else arr
        
        if isinstance(arr, Generator) or self.stream_mode:
            return self._stream_sort_and_collect(arr)

        if self.profile:
            if not hasattr(self, 'profiler') or self.profiler is None:
                self.profiler = cProfile.Profile()
                self.profiler.enable()

        try:
            if isinstance(arr, list):
                arr = np.array(arr, dtype=np.float64)
                
            if len(arr) > self.external_sort_threshold:
                self.logger.info(f"Using external sort for {len(arr):,} elements.")
                strategy = SortStrategy.EXTERNAL_SORT
            elif self.use_ml_prediction:
               strategy = self._predict_strategy(arr)
            elif self.strategy == SortStrategy.AUTO:
               strategy = self._choose_optimal_strategy(arr)
            else:
                strategy = self.strategy
                
            self.logger.info(f"Selected strategy: {strategy.value}")

            with performance_tracker():
                if strategy == SortStrategy.MEMORY_EFFICIENT:
                    result = self._memory_efficient_sort(arr)
                elif strategy == SortStrategy.HYBRID:
                    result = (self._hybrid_sort(arr),
                             self._calculate_stats(arr, "hybrid", Algorithm.INTROSORT.value))
                elif strategy == SortStrategy.ADAPTIVE:
                    result = self._adaptive_sort(arr)
                elif strategy == SortStrategy.STREAM:
                    return self._stream_sort_and_collect(arr)
                elif strategy == SortStrategy.BLOCK_SORT:
                    result = self._advanced_block_sort(arr)
                elif strategy == SortStrategy.BUCKET_SORT:
                    result = self._bucket_sort(arr)
                elif strategy == SortStrategy.RADIX_SORT:
                    result = (self._radix_sort(arr), self._calculate_stats(arr, "radix", Algorithm.RADIXSORT.value))
                elif strategy == SortStrategy.COMPRESSION_SORT:
                    result, compression_ratio = self._compression_sort(arr)
                    stats = self._calculate_stats(arr, "compression", Algorithm.MERGESORT.value, compression_ratio=compression_ratio)
                    result = (result, stats)
                elif strategy == SortStrategy.EXTERNAL_SORT:
                    result = asyncio.run(self._external_sort(arr))
                    stats = self._calculate_stats(arr, "external", Algorithm.EXTERNALMERGESORT.value)
                    result = (result, stats)
                else:
                    result = self._parallel_sort(arr)

            if self.profile:
                self.profiler.disable()
                s = io.StringIO()
                ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
                ps.print_stats()
                self.logger.debug(f"Profile results:\n{s.getvalue()}")

            is_sorted = np.all(result[0][:-1] <= result[0][1:]) if isinstance(result, tuple) else np.all(result[:-1] <= result[1:])
            if not is_sorted:
              self.logger.warning(f"Sort verification failed, switching to fallback strategy: {self.fallback_strategy}")
              fallback_result = np.sort(arr, kind = "stable")
              fallback_stats = self._calculate_stats(arr, "fallback", self.fallback_strategy.value, error_detected = True)

              self.logger.info("Sort operation completed successfully with fallback")
              return fallback_result, fallback_stats

            self.logger.info("Sort operation completed successfully")
            return result


        except Exception as e:
            self.logger.error(f"Error during sorting: {e}", exc_info=True)
            return original_arr, self._calculate_stats(original_arr, "failed", "none", error=e)

    def _setup_logging(self):
        self.logger = logging.getLogger(f"{__name__}.{id(self)}")
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)

    @contextmanager
    def _resource_monitor(self):
        start_mem = psutil.Process().memory_info().rss
        start_time = time.perf_counter()

        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_mem = psutil.Process().memory_info().rss

            self.metrics.record('memory_delta', end_mem - start_mem)
            self.metrics.record('operation_time', end_time - start_time)

    def _adaptive_chunk_size(self, arr_size: int, itemsize: int) -> int:
        available_memory = psutil.virtual_memory().available
        total_size = arr_size * itemsize
        cpu_count = psutil.cpu_count()

        l3_cache = psutil.cpu_count() * 2 ** 20

        if total_size < l3_cache:
            return min(arr_size, 10000)

        optimal_chunks = max(
            cpu_count,
            int(total_size / (available_memory * self.adaptive_threshold))
        )

        return max(1000, arr_size // optimal_chunks)

    def _advanced_partition(self, arr: npt.NDArray) -> List[npt.NDArray]:
        if len(arr) < 1000:
            return [arr]

        quantiles = np.linspace(0, 100, min(len(arr) // 1000 + 1, 10))
        pivots = np.percentile(arr, quantiles)

        partitions = []
        start_idx = 0

        for i in range(1, len(pivots)):
            mask = (arr >= pivots[i - 1]) & (arr < pivots[i])
            partition = arr[mask]
            if len(partition) > 0:
                partitions.append(partition)

        return partitions

    def _hybrid_sort(self, arr: npt.NDArray) -> npt.NDArray:
        if len(arr) < 1000:
            return np.sort(arr)

        partitions = self._advanced_partition(arr)

        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            sorted_partitions = list(executor.map(np.sort, partitions))

        return np.concatenate(sorted_partitions)

    def _merge_sorted_arrays(self, arrays: List[npt.NDArray]) -> npt.NDArray:
        merged = []
        heap = []

        for i, arr in enumerate(arrays):
            if len(arr) > 0:
                heapq.heappush(heap, (arr[0], i, 0))

        while heap:
            val, arr_idx, elem_idx = heapq.heappop(heap)
            merged.append(val)

            if elem_idx + 1 < len(arrays[arr_idx]):
                next_val = arrays[arr_idx][elem_idx + 1]
                heapq.heappush(heap, (next_val, arr_idx, elem_idx + 1))

        return np.array(merged)

    def _adaptive_sort(self, arr: npt.NDArray) -> Tuple[npt.NDArray, SortStats]:
        n = len(arr)

        sample = arr[np.random.choice(n, min(1000, n), replace=False)]
        std_dev = np.std(sample)
        is_nearly_sorted = np.sum(np.diff(sample) < 0) < len(sample) * 0.1

        if is_nearly_sorted:
            algorithm = Algorithm.TIMSORT
            with self._resource_monitor():
                result = np.sort(arr, kind='stable')
        elif std_dev < (np.max(sample) - np.min(sample)) / 100:
            algorithm = Algorithm.QUICKSORT
            with self._resource_monitor():
                result = self._parallel_sort(arr)[0]
        else:
            algorithm = Algorithm.MERGESORT
            with self._resource_monitor():
                result = self._hybrid_sort(arr)

        return result, self._calculate_stats(arr, "adaptive", algorithm.value)

    def _optimize_bucket_count(self, arr: npt.NDArray) -> int:
        n = len(arr)
        if n < 1000:
            return max(1, n // 10)

        cache_key = f"bucket_count_{n}_{arr.std():.2f}"
        if cached_value := self.cache.get(cache_key):
            return cached_value

        sample_size = min(1000, n)
        sample = arr[np.random.choice(n, sample_size, replace=False)]
        std_dev = np.std(sample)
        range_size = np.ptp(sample)

        if std_dev < range_size / 100:
            bucket_count = int(math.sqrt(n))
        else:
            density = n / range_size if range_size > 0 else 1
            bucket_count = int(min(
                math.sqrt(n) * (std_dev / range_size) * 2,
                n / math.log2(n)
            ))

        self.cache.put(cache_key, bucket_count)
        return bucket_count
    
    def _calculate_stats(self, arr: npt.NDArray, strategy: str, algorithm: str, error: Optional[Exception] = None, stream_chunks: int = 0, compression_ratio: float = 1.0, error_detected: bool = False) -> SortStats:
        process = psutil.Process()

        performance = PerformanceMetrics(
            cpu_time=time.process_time(),
            wall_time=time.perf_counter() - self.start_time,
            memory_peak=process.memory_info().rss / (1024 * 1024),
            cache_hits=self.cache.hits,
            cache_misses=self.cache.misses,
            thread_count=len(process.threads()),
            context_switches=process.num_ctx_switches().voluntary
        )

        if error:
             return SortStats(
                execution_time=time.perf_counter() - self.start_time,
                memory_usage=process.memory_info().rss / (1024 * 1024),
                items_processed=len(arr),
                cpu_usage=psutil.cpu_percent(),
                bucket_distribution=[],
                strategy_used=strategy,
                algorithm_used="none",
                performance=performance,
                optimization_history=self.metrics.metrics,
                stream_chunks = stream_chunks,
                compression_ratio = compression_ratio,
                error_detected=True,
             )

        return SortStats(
            execution_time=performance.wall_time,
            memory_usage=performance.memory_peak,
            items_processed=len(arr),
            cpu_usage=psutil.cpu_percent(),
            bucket_distribution=self._get_bucket_distribution(arr),
            strategy_used=strategy,
            algorithm_used=algorithm,
            performance=performance,
            optimization_history=self.metrics.metrics,
            stream_chunks = stream_chunks,
            compression_ratio = compression_ratio,
            error_detected = error_detected,
        )
    
    def _choose_optimal_strategy(self, arr: npt.NDArray) -> SortStrategy:
        n = len(arr)

        sample_size = min(1000, n)
        sample = arr[np.random.choice(n, sample_size, replace=False)]

        is_nearly_sorted = np.sum(np.diff(sample) < 0) < len(sample) * 0.1
        std_dev = np.std(sample)
        range_size = np.ptp(sample)
        memory_available = psutil.virtual_memory().available
        data_skewness = skew(sample)
        data_kurtosis = kurtosis(sample)
        
        estimated_memory = n * arr.itemsize * 3
        
        if estimated_memory > memory_available * 0.7:
            return SortStrategy.MEMORY_EFFICIENT
        
        if data_skewness > 2 or data_kurtosis > 5 :
            return SortStrategy.BUCKET_SORT
        
        if is_nearly_sorted:
            return SortStrategy.ADAPTIVE

        if n > 1_000_000 and psutil.cpu_count() > 2:
            return SortStrategy.PARALLEL
        
        if std_dev < range_size / 100:
            return SortStrategy.HYBRID
        
        if n > self.external_sort_threshold:
            return SortStrategy.EXTERNAL_SORT
            
        return SortStrategy.ADAPTIVE

    def _get_bucket_distribution(self, arr: npt.NDArray) -> List[int]:
        if len(arr) == 0:
            return []

        n_buckets = self._optimize_bucket_count(arr)
        bucket_ranges = np.linspace(arr.min(), arr.max(), n_buckets + 1)
        distribution = []

        for i in range(n_buckets):
            mask = (arr >= bucket_ranges[i]) & (arr < bucket_ranges[i + 1])
            distribution.append(int(np.sum(mask)))

        return distribution

    def _parallel_sort(self, arr: npt.NDArray) -> Tuple[npt.NDArray, SortStats]:
        chunk_size = self._adaptive_chunk_size(len(arr), arr.itemsize)
        chunks = np.array_split(arr, max(1, len(arr) // chunk_size))

        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            sorted_chunks = list(executor.map(np.sort, chunks))

        result = self._merge_sorted_arrays(sorted_chunks)
        return result, self._calculate_stats(arr, "parallel", Algorithm.QUICKSORT.value)

    def _memory_efficient_sort(self, arr: npt.NDArray) -> Tuple[npt.NDArray, SortStats]:
        chunk_size = self._adaptive_chunk_size(len(arr), arr.itemsize)
        result = np.zeros_like(arr)

        for i in range(0, len(arr), chunk_size):
            chunk = arr[i:i + chunk_size]
            np.sort(chunk, out=chunk)
            result[i:i + chunk_size] = chunk

        return result, self._calculate_stats(arr, "memory_efficient", Algorithm.MERGESORT.value)
    
    

def benchmark(
    sorter: EnhancedHyperionSort,
    sizes: List[int],
    runs: int = 3,
    save_results: bool = True
) -> Dict[str, Any]:
    results = []

    for size in sizes:
        size_results = []
        for run in range(runs):
            logger.info(f"\nBenchmarking với {size:,} phần tử (Run {run + 1}/{runs}):")

            if run == 0:
                data = np.random.randint(0, size * 10, size=size)
            elif run == 1:
                data = np.sort(np.random.randint(0, size * 10, size=size))
                data[::100] = np.random.randint(0, size * 10, size=len(data[::100]))
            else:
                n_clusters = 10
                cluster_points = size // n_clusters
                clusters = []

                for i in range(n_clusters):
                    center = np.random.randint(0, size * 10)
                    cluster = np.random.normal(loc=center,
                                                scale=size / 100,
                                                size=cluster_points)
                    clusters.append(cluster)

                data = np.concatenate(clusters).astype(np.int32)
            
            sorted_arr, metrics = sorter.sort(data)
            
            
            if isinstance(metrics, tuple):
              metrics = metrics[1]
              sorted_arr = sorted_arr[0]
            
            is_sorted = np.all(sorted_arr[:-1] <= sorted_arr[1:])

            print(f"\n✨ Kết quả chạy {run + 1}:")
            print(f"✓ Đã sort xong!")
            print(f"⚡ Thời gian thực thi: {metrics.execution_time:.4f} giây")
            print(f"⏱️ CPU time: {metrics.performance.cpu_time:.4f} giây")
            print(f"💾 Bộ nhớ sử dụng: {metrics.memory_usage:.2f} MB")
            print(f"🖥️ CPU usage: {metrics.cpu_usage:.1f}%")
            print(f"🚀 Tốc độ xử lý: {size/metrics.execution_time:,.0f} items/giây")
            print(f"🎯 Strategy: {metrics.strategy_used}")
            print(f"🔄 Algorithm: {metrics.algorithm_used}")
            print(f"✓ Kết quả đúng: {is_sorted}")
            if metrics.error_detected :
               print(f"🚨 Fallback used: {metrics.fallback_strategy}")
            if metrics.compression_ratio < 1.0:
              print(f"🗜️ Compression ratio: {metrics.compression_ratio:.2f}")
            

            result_data = {
                'size': size,
                'run': run,
                'distribution': ['random', 'nearly_sorted', 'clustered'][run],
                'time': metrics.execution_time,
                'cpu_time': metrics.performance.cpu_time,
                'memory': metrics.memory_usage,
                'strategy': metrics.strategy_used,
                'algorithm': metrics.algorithm_used,
                'items_per_second': size / metrics.execution_time,
                'is_sorted': is_sorted,
                'compression_ratio': metrics.compression_ratio,
                'fallback_strategy' : metrics.fallback_strategy
            }

            size_results.append(result_data)

        avg_time = np.mean([r['time'] for r in size_results])
        std_time = np.std([r['time'] for r in size_results])

        print(f"\n📊 Thống kê cho {size:,} phần tử:")
        print(f"📈 Thời gian trung bình: {avg_time:.4f} ± {std_time:.4f} giây")
        print(f"🎯 Độ ổn định: {(1 - std_time / avg_time) * 100:.2f}%")

        results.extend(size_results)

    if save_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_results_{timestamp}.pkl"

        with open(filename, 'wb') as f:
            pickle.dump(results, f)

        print(f"\n💾 Đã lưu kết quả vào: {filename}")

    return {
        'results': results,
        'summary': {
            'total_runs': len(results),
            'sizes_tested': sizes,
            'best_performance': min(results, key=lambda x: x['time']),
            'worst_performance': max(results, key=lambda x: x['time'])
        }
    }


if __name__ == "__main__":
    sorter = EnhancedHyperionSort(
        strategy=SortStrategy.AUTO,
        profile=True,
        cache_size=2000,
        adaptive_threshold=0.8,
        use_ml_prediction = True,
        external_sort_threshold=1000000
    )

    test_sizes = [100_000, 1_000_000, 10_000_000, 20_000_000]
    benchmark_results = benchmark(
        sorter=sorter,
        sizes=test_sizes,
        runs=3,
        save_results=True
    )

    def data_generator():
        for i in range(1000000):
            yield np.random.randint(0, 1000)

    sorter = EnhancedHyperionSort(
        strategy=SortStrategy.STREAM,
        profile=True,
        cache_size=2000,
        adaptive_threshold=0.8,
        stream_mode=True,
        use_ml_prediction = False
    )

    sorted_arr, stream_stats = sorter.sort(data_generator())
    print(f"Stream sort completed, total chunks: {stream_stats.stream_chunks}")
    print(f"Stream sort time : {stream_stats.execution_time:.4f} seconds")
    print(f"Stream sorted item: {len(sorted_arr):,} items")

    print("\n🌟 Kết quả tổng quan:")
    print(f"📊 Tổng số lần chạy: {benchmark_results['summary']['total_runs']}")
    print("\n🏆 Hiệu suất tốt nhất:")
    best = benchmark_results['summary']['best_performance']
    print(f"- Kích thước: {best['size']:,}")
    print(f"- Thời gian: {best['time']:.4f} giây")
    print(f"- Strategy: {best['strategy']}")
    print(f"- Distribution: {best['distribution']}")