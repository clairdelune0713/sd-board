# SD Board API Reference

The SD Board API provides a single endpoint to generate high-resolution 4K storyboards by orchestrating data from Supabase and Cloudflare R2.

## Base URL

By default, the server runs on:
`http://localhost:8005`

---

## Endpoints

### 1. Generate Storyboard
`POST /generate-storyboard`

Generates a 4K resolution storyboard image in JPEG format. The process involves:
1. Fetching scene metadata and dialogue from Supabase.
2. Downloading 4 frame images and 1 environment image from Cloudflare R2.
3. Downloading character portraits from R2.
4. Rendering the final composite image with dynamic text wrapping.
5. Uploading the final PNG version back to R2.
6. Returning the JPEG version in the response.

#### Request Body
The request must be a JSON object with the following fields:

| Field | Type | Description |
| :--- | :--- | :--- |
| `user_email` | `string` | The email address of the user (used for R2 path prefixing). |
| `project` | `string` | The unique project identifier/slug. |
| `storyboard_number` | `integer` | The ID of the storyboard to generate. |

**Example:**
```json
{
  "user_email": "henry@example.com",
  "project": "cinematic-short-2024",
  "storyboard_number": 1
}
```

#### Response
- **Status 200 (OK):** Returns a raw binary stream of the generated JPEG image.
- **Content-Type:** `image/jpeg`

#### Error Responses
| Code | Description |
| :--- | :--- |
| `400 Bad Request` | Invalid input or mismatch in data (e.g., expected 4 panels but found fewer). |
| `422 Unprocessable Entity` | Missing required fields in JSON body. |
| `500 Internal Server Error` | Failed to fetch data from Supabase/R2 or rendering engine error. |

#### Example Usage (cURL)
```bash
curl -X POST http://localhost:8005/generate-storyboard \
     -H "Content-Type: application/json" \
     -d '{
       "user_email": "user@example.com",
       "project": "project-id-123",
       "storyboard_number": 1
     }' \
     --output storyboard.jpg
```

---

## Technical Details

### R2 Storage Pattern
The API expects and produces files at the following paths in the configured R2 bucket:

- **Input Frames:** `movie-script/{user_email}/{project}/boards/board-{sb_num}-{1..4}.png`
- **Character Inputs:** `movie-script/{user_email}/{project}/inputs/`
- **Final Output:** `movie-script/{user_email}/{project}/boards/comp-{sb_num}.png`

### Dynamic Height
The output image has a fixed width of **2880px**. The height is calculated dynamically based on the volume of dialogue and action text to ensure no content is clipped.
