# Cloud Image Processor API

## Project Overview

**Cloud Image Processor API** is a backend service that accepts image uploads, stores the original files in cloud object storage, and generates thumbnails asynchronously using background workers.

The system is designed to mimic production-style media processing pipelines used by large platforms that manage user-generated images. It separates file storage, metadata storage, and image processing into independent services to ensure scalability and reliability.

The project emphasizes clean backend architecture, asynchronous processing, and containerized infrastructure.

---

## Key Features

- **Image Upload API**
  - Upload images through a REST endpoint
  - Automatically generates a unique image ID
  - Stores original images in AWS S3

- **Asynchronous Thumbnail Processing**
  - Background worker generates thumbnails
  - Redis queue manages image processing jobs
  - Upload returns immediately while processing runs asynchronously

- **Variant-Based Image Storage**
  - Supports multiple versions of the same image
  - Original image
  - Thumbnail image
  - Designed to support additional variants (medium, webp, etc.)

- **Presigned URL Delivery**
  - Images are served directly from S3
  - Backend generates secure presigned download URLs
  - Avoids routing large files through the API server

- **Metadata Management**
  - Postgres database stores image metadata
  - Normalized schema for image variants
  - Stores dimensions, content type, and size

- **Image Listing and Retrieval**
  - Retrieve metadata for a specific image
  - Paginated listing endpoint for stored images

- **Containerized Infrastructure**
  - Docker Compose orchestrates all services
  - Independent API and worker containers
  - Local development mirrors production-style architecture

---

## Tech Stack

This project uses a modern backend architecture similar to production cloud services.

### Backend
- **FastAPI (Python)**
- RESTful API design
- SQLAlchemy ORM

### Database
- **Postgres**
- Managed with SQLAlchemy models

### Object Storage
- **AWS S3**
- Presigned URL generation

### Background Processing
- **Redis**
- **RQ workers**

### Image Processing
- **Pillow**

### Infrastructure
- **Docker**
- **Docker Compose**

---

## Architecture Overview

The system separates responsibilities across several services.

Client uploads are handled by the API server, while image processing runs asynchronously in a worker.

```
Client
   │
   ▼
FastAPI API Server
   │
   ├── Postgres (metadata)
   │
   ├── AWS S3 (image storage)
   │
   └── Redis (job queue)
           │
           ▼
        Worker
   (thumbnail generator)
```

This architecture allows image processing to scale independently of the API server.

---

## Image Upload Flow

Endpoint:

```
POST /images
```

Upload pipeline:

1. Client uploads an image
2. API generates a UUID for the image
3. Original image is uploaded to S3
4. Metadata is stored in Postgres
5. Thumbnail job is added to the Redis queue
6. API returns the image ID immediately

Example response:

```
{
  "id": "df3e22c8-e744-45bc-8883-f35d404e5914"
}
```

The heavy image processing work happens asynchronously in the worker service.

---

## Background Processing Pipeline

The worker processes jobs from the Redis queue.

Processing pipeline:

1. Download original image from S3
2. Generate a thumbnail (300x300)
3. Upload thumbnail to S3
4. Insert thumbnail variant into the database
5. Update parent image dimensions

This asynchronous pipeline allows uploads to remain fast even when image processing is expensive.

---

## Image Retrieval

Endpoint:

```
GET /images/{id}
```

Returns image metadata along with presigned URLs for each variant.

Example response:

```
{
  "id": "df3e22c8-e744-45bc-8883-f35d404e5914",
  "width": 300,
  "height": 300,
  "variants": [
    {
      "variant": "original",
      "url": "...",
      "width": 300,
      "height": 300
    },
    {
      "variant": "thumbnail",
      "url": "...",
      "width": 300,
      "height": 300
    }
  ]
}
```

Images are downloaded directly from S3 rather than being proxied through the API server.

---

## Image Listing

Endpoint:

```
GET /images
```

Provides paginated results containing stored image metadata and variant information.

Example response:

```
{
  "items": [...],
  "page": 1,
  "page_size": 20,
  "total": 4
}
```

---

## Database Design

The service uses a variant-based storage model.

Images table:

```
images
------
id
created_at
content_type
size_bytes
width
height
```

Variants table:

```
image_variants
--------------
image_id
variant
s3_key
content_type
size_bytes
width
height
```

This design allows the system to support multiple image formats and sizes for the same asset.

---

## Local Development Setup

To run the project locally you need:

- Docker
- Docker Compose

---

### 1. Clone Repository

```
git clone https://github.com/YOUR_USERNAME/cloud-image-processor-api
cd cloud-image-processor-api
```

---

### 2. Start Services

```
docker compose up --build
```

This launches:

- FastAPI API server
- Postgres database
- Redis queue
- Background worker

The API will be available at:

```
http://localhost:8000
```

Interactive API docs:

```
http://localhost:8000/docs
```

---

## Example Requests

Upload an image:

```
curl -X POST -F "file=@test.jpg" http://localhost:8000/images
```

Retrieve an image:

```
curl http://localhost:8000/images/{id}
```

List images:

```
curl http://localhost:8000/images
```

---

## Engineering Concepts Demonstrated

This project highlights several backend engineering patterns:

- Object storage architecture (S3 for files, Postgres for metadata)
- Asynchronous background job processing
- Variant-based asset pipelines
- Secure file delivery using presigned URLs
- Containerized microservice-style infrastructure
- Scalable image processing workflows

---

## Project Goals

The goal of this project was to build a production-style backend service that demonstrates real-world backend system design principles including asynchronous processing, distributed services, and scalable media storage.

---

## License

MIT
