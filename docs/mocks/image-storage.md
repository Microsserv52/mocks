# Image storage mock

The image-storage mock emulates the object operations used by the Product image
flow: presigned-style upload, validation, attachment, public media reads, and
deletion. Objects are stored on disk so a Docker volume can preserve them across
container restarts.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `IMAGE_STORAGE_DATA_DIR` | `/data` | Root directory for objects and content-type metadata. |
| `IMAGE_STORAGE_PORT` | `8090` | HTTP listen port. |

## Endpoints

| Method and path | Behavior |
| --- | --- |
| `GET /health` | Returns the liveness status. |
| `PUT /upload/{key}` | Stores a pending upload. |
| `GET /object/{key}` | Reads an object for service-to-service validation. |
| `PUT /object/{key}` | Writes an object directly. |
| `DELETE /object/{key}` | Deletes the object and its content-type metadata. |
| `GET /media/{key}` | Serves the object through the public media contract. |

`PUT` requests accept at most 5 MiB. Supplying `If-None-Match: *` prevents an
existing key from being overwritten and returns HTTP `412` when it already
exists.

```bash
curl -X PUT http://localhost:8090/upload/pending/products/example/original.jpg \
  -H 'Content-Type: image/jpeg' \
  -H 'If-None-Match: *' \
  --data-binary @photo.jpg
```

## Key safety

Keys must be relative path segment lists. The mock rejects empty segments,
`.` and `..`, backslashes, absolute paths, and segments ending in `.ctype`.
The latter suffix is reserved for internal content-type sidecar files.

An incomplete request body is rejected before an existing object is replaced.
Writing an object without `Content-Type` removes old sidecar metadata; later
reads infer a media type from the filename and otherwise use
`application/octet-stream`.
