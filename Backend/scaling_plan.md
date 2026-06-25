Scaling the backend to handle concurrent users requires moving from a single-server, synchronous architecture to a distributed, asynchronous system. Based on the current codebase, here is a technical roadmap to achieve this:

1. Asynchronous Task Processing (Crucial)
Currently, endpoints like /teardown/generate-pdf block the request for 30s+ while the LLM and search phases run. This will quickly exhaust server threads under load.

Implement Celery + Redis/RabbitMQ: Move the run_product_pipeline and PDF generation into background tasks.
Workflow:
User hits POST /generate-pdf.
Backend returns a 202 Accepted with a task_id immediately.
A background worker (Celery) processes the heavy lifting.
Frontend polls GET /task-status/{task_id} or receives a notification via WebSockets/Webhooks when done.
2. Distributed Caching
The current Tavily search cache in voice_analysis.py uses @lru_cache, which is local to a single process.

97|@lru_cache(maxsize=128)
98|def _tavily_competitor_search_cached(competitor_name: str) -> str:
Move to Redis: Replace lru_cache with a shared Redis instance. This allows multiple server instances to share the same research data, drastically reducing API costs and latency for common competitor searches.
3. Horizontal Scaling & Load Balancing
The current setup likely runs a single Uvicorn process.

Process Management: Use Gunicorn with Uvicorn workers (-k uvicorn.workers.UvicornWorker) to utilize all CPU cores on a single machine.
Containerization: Wrap the app in Docker.
Orchestration: Deploy to AWS ECS or Kubernetes. Use an Application Load Balancer (ALB) or Nginx to distribute traffic across multiple containers.
4. Cloud Storage for Assets
Currently, PDFs are saved to a local output/ folder (pdf_generator.py). In a multi-server setup, a PDF generated on Server A won't be available for download on Server B.

AWS S3 / Google Cloud Storage: Replace local file writes with uploads to an S3 bucket.
Pre-signed URLs: Instead of serving files through FastAPI, return a temporary S3 pre-signed URL for the user to download the PDF directly from the cloud provider, reducing load on your backend.
5. Database Optimization
The current db.py uses a simple SQLAlchemy engine.

Connection Pooling: Ensure create_engine is configured with a pool size and max overflow (SQLAlchemy does this by default, but it needs tuning for high concurrency).
PgBouncer: For very high concurrency, use PgBouncer as a middleware to manage thousands of database connections efficiently.
6. Rate Limiting & Security
Expensive LLM routes (Groq 70B) and Search APIs (Tavily) need protection from abuse.

API Gateway: Use a tool like Kong or AWS API Gateway to enforce rate limits per user/IP.
Middleware: Use slowapi in FastAPI to limit how many teardowns a single user can generate per hour.
Summary Roadmap
Phase	Action	Benefit
Immediate
Celery + Redis
Prevents request timeouts; handles long tasks in background.
Short-term
Docker + S3
Enables horizontal scaling and persistent file storage.
Mid-term
Redis Cache
Reduces external API costs and speeds up repeat queries.
Long-term
Load Balancer
Distributes traffic across multiple global regions.
