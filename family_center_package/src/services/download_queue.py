"""
Download queue management module for handling concurrent downloads with bandwidth limiting.
"""

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Queue
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DownloadTask:
    """Represents a download task in the queue."""

    file_id: str
    destination_path: str
    size_bytes: int
    created_time: datetime
    priority: int = 0
    retry_count: int = 0
    download_callback: Callable[["DownloadTask"], None] | None = None
    error_callback: Callable[["DownloadTask"], None] | None = None
    last_error: str | None = None
    file_metadata: dict[str, Any] | None = None


class DownloadQueue:
    """Manages concurrent downloads with bandwidth limiting."""

    def __init__(
        self, max_workers: int = 3, max_retries: int = 3, retry_delay_seconds: int = 5
    ):
        """Initialize the download queue.

        Args:
            max_workers: Maximum number of concurrent downloads
            max_retries: Number of retry attempts for failed downloads
            retry_delay_seconds: Delay between retry attempts in seconds
        """
        self.queue: Queue[DownloadTask] = Queue()
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.workers: list[threading.Thread] = []
        self.stop_event = threading.Event()
        self._lock = threading.Lock()
        self._active_tasks: dict[str, DownloadTask] = {}
        self._start_workers()

    def _start_workers(self) -> None:
        """Start worker threads for processing downloads."""
        for _ in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.workers.append(worker)

    def _worker_loop(self) -> None:
        """Main worker loop that processes download tasks."""
        while not self.stop_event.is_set():
            try:
                task = self.queue.get(timeout=1)
                try:
                    self._process_task(task)
                except Exception as e:
                    logger.error(
                        f"Error processing task for file {task.file_id}: {str(e)}"
                    )
                    self._handle_task_error(task, str(e))
                finally:
                    self.queue.task_done()
            except Empty:
                continue

    def _process_task(self, task: DownloadTask) -> None:
        """Process a single download task."""
        try:
            if task.download_callback:
                task.download_callback(task)
            # Only remove from active tasks if successful
            with self._lock:
                self._active_tasks.pop(task.file_id, None)
        except Exception as e:
            # Let the error propagate to _handle_task_error
            task.last_error = str(e)
            raise

    def _handle_task_error(self, task: DownloadTask, error: str) -> None:
        """Handle errors that occur during task processing."""
        task.last_error = error
        task.retry_count += 1

        if task.retry_count <= self.max_retries:
            logger.info(
                f"Retrying task for file {task.file_id} (attempt {task.retry_count + 1})"
            )
            time.sleep(self.retry_delay_seconds)
            # Create a new task to ensure clean state
            new_task = DownloadTask(
                file_id=task.file_id,
                destination_path=task.destination_path,
                size_bytes=task.size_bytes,
                created_time=task.created_time,
                priority=task.priority,
                retry_count=task.retry_count,
                download_callback=task.download_callback,
                error_callback=task.error_callback,
                last_error=task.last_error,
                file_metadata=task.file_metadata,
            )
            self.queue.put(new_task)
            with self._lock:
                self._active_tasks[task.file_id] = new_task
        else:
            logger.error(
                f"Task for file {task.file_id} failed after {task.retry_count} attempts"
            )
            if task.error_callback:
                task.error_callback(task)
            with self._lock:
                self._active_tasks.pop(task.file_id, None)

    def add_task(
        self,
        file_id: str,
        destination_path: str,
        size_bytes: int,
        created_time: datetime,
        priority: int = 0,
        download_callback: Callable[[DownloadTask], None] | None = None,
        error_callback: Callable[[DownloadTask], None] | None = None,
        file_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a download task to the queue.

        Args:
            file_id: ID of the file to download
            destination_path: Path where the file should be saved
            size_bytes: Size of the file in bytes
            created_time: When the file was created
            priority: Task priority (higher number = higher priority)
            download_callback: Optional callback function to handle the download
            error_callback: Optional callback function to handle download failures
            file_metadata: Optional metadata about the file from Google Drive
        """
        task = DownloadTask(
            file_id=file_id,
            destination_path=destination_path,
            size_bytes=size_bytes,
            created_time=created_time,
            priority=priority,
            download_callback=download_callback,
            error_callback=error_callback,
            file_metadata=file_metadata,
        )
        with self._lock:
            if file_id in self._active_tasks:
                logger.warning(f"Task for file {file_id} already exists")
                return
            self._active_tasks[file_id] = task
        self.queue.put(task)
        logger.debug(f"Added download task for {destination_path} to queue")

    def stop(self) -> None:
        """Stop all worker threads and clear the queue."""
        print("DownloadQueue: Setting stop event")
        self.stop_event.set()

        print("DownloadQueue: Waiting for worker threads")
        for worker in self.workers:
            print(f"DownloadQueue: Waiting for thread {worker.name}")
            worker.join(timeout=1.0)
            if worker.is_alive():
                print(f"DownloadQueue: Thread {worker.name} did not stop in time")
                # Force clear the queue to help threads exit
                while not self.queue.empty():
                    try:
                        self.queue.get_nowait()
                        self.queue.task_done()
                    except Empty:
                        break

        print("DownloadQueue: Clearing queue")
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except Empty:
                break
        self._active_tasks.clear()
        print("DownloadQueue: Stop complete")

    def get_queue_size(self) -> int:
        """Get the current number of tasks in the queue."""
        return self.queue.qsize()

    def wait_for_completion(self) -> None:
        """Wait for all tasks in the queue to complete."""
        logger.info("Waiting for all download tasks to complete...")
        self.queue.join()
        logger.info("All download tasks completed")

    def get_active_tasks(self) -> dict[str, DownloadTask]:
        """Get a copy of the currently active tasks."""
        with self._lock:
            return dict(self._active_tasks)
