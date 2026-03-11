"""
Celery Application Configuration for Bharat Shorts

Production-ready setup with:
- Priority queues (critical, gpu, default, low)
- Task routing by operation type
- Concurrency tuning for CPU-heavy video processing
- Result expiration and retry policies
- Flower monitoring support
"""

import os
from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "bharat_shorts",
    broker=redis_url,
    backend=redis_url,
    include=["workers.tasks"],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="Asia/Kolkata",
    enable_utc=True,

    # Task tracking
    task_track_started=True,
    task_send_sent_event=True,
    worker_send_task_events=True,

    # Limits
    task_time_limit=1800,       # 30 min hard limit
    task_soft_time_limit=1500,  # 25 min soft limit (raises SoftTimeLimitExceeded)
    worker_max_tasks_per_child=20,  # Restart worker after 20 tasks (prevent memory leaks)
    worker_max_memory_per_child=2_000_000,  # 2GB max memory per worker

    # Results
    result_expires=86400,  # Results expire after 24 hours
    result_extended=True,  # Store task args/kwargs in result

    # Retry
    task_acks_late=True,    # Acknowledge after completion (survive worker crash)
    task_reject_on_worker_lost=True,

    # Concurrency — CPU-heavy tasks need limited concurrency
    worker_concurrency=int(os.getenv("CELERY_CONCURRENCY", "2")),
    worker_prefetch_multiplier=1,  # Don't prefetch (tasks are long-running)

    # Priority queues
    task_queues={
        "critical": {"exchange": "critical", "routing_key": "critical"},
        "gpu": {"exchange": "gpu", "routing_key": "gpu"},
        "default": {"exchange": "default", "routing_key": "default"},
        "low": {"exchange": "low", "routing_key": "low"},
    },
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",

    # Route tasks to appropriate queues
    task_routes={
        "transcribe_video": {"queue": "gpu"},
        "render_video": {"queue": "gpu"},
        "render_video_4k": {"queue": "gpu"},
        "assemble_video": {"queue": "default"},
        "eye_contact_fix": {"queue": "gpu"},
        "dynamic_reframe": {"queue": "gpu"},
        "generate_avatar": {"queue": "gpu"},
        "generate_dub": {"queue": "default"},
        "add_sfx": {"queue": "low"},
        "process_video_full": {"queue": "default"},
    },

    # Rate limiting
    task_annotations={
        "transcribe_video": {"rate_limit": "10/m"},
        "render_video_4k": {"rate_limit": "2/m"},
        "generate_avatar": {"rate_limit": "5/m"},
    },
)
