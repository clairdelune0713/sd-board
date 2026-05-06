# SD Board - 4K Cinematic Storyboard Generator

A high-performance Python application designed to generate professional, 4K resolution cinematic storyboards. It orchestrates data from Supabase (metadata/text), Cloudflare R2 (images), and provides a beautifully composed 2x2 grid layout with dynamic height support.

## Key Features

- **4K Resolution**: Generates high-fidelity images at 2880xDYNAMIC (3:4 ratio base).
- **Dynamic Height Engine**: Automatically calculates the required canvas height based on the text length for each panel, ensuring no content is ever cut off.
- **Vision-Optimized Layout**: Maintains original image aspect ratios without black margins or cropping.
- **Multi-Language Support**: Full native support for Japanese, Korean, Simplified/Traditional Chinese, and French via unified CJK-compatible font rendering.
- **Automated Data Fetching**:
  - **Supabase**: Fetches project metadata and scene content from `cinedual_projects` and `cine_action_dialogues`.
  - **Cloudflare R2**: Retrieves storyboard frames from `/boards/` and character portraits from `/inputs/`.
- **Clean Formatting**: Automatically cleans character tags (e.g., `@John_Doe-1234` -> `John Doe`) for a professional look.

## Prerequisites

- [uv](https://github.com/astral-sh/uv) (Highly recommended Python package manager)
- Python 3.12+
- Cloudflare R2 Bucket
- Supabase Database (PostgreSQL)

## Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd sd-board

# Install dependencies
uv sync
```

## Configuration

Create a `.env` file in the root directory:

```ini
DATABASE_URL=postgresql://user:pass@host:port/db
S3_ENDPOINT=https://<account_id>.r2.cloudflarestorage.com
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_BUCKET_R2=aifx-studio
```

## Usage

### Command Line Interface (CLI)

Generate a storyboard by passing a JSON configuration file:

```bash
PYTHONPATH=. uv run python src/main.py --json test.json --out output.jpg
```

**Example `test.json`:**
```json
{
  "user_email": "user@example.com",
  "project": "20260506-1540-A",
  "storyboard_number": 1
}
```

### FastAPI Server

Run the standalone API server:

```bash
uv run python src/main.py serve
```

The API will be available at `http://0.0.0.0:8005`. You can access the interactive documentation at `/docs`.

**Endpoint:** `POST /generate-storyboard`
- Returns a 4K JPEG image stream.

## Project Structure

- `src/main.py`: Entry point for CLI and FastAPI server.
- `src/services/data_fetcher.py`: Handles Supabase queries and R2 image downloads.
- `src/services/storyboard_builder.py`: Core rendering engine using Pillow.
- `src/config.py`: Environment variable management.

## License

MIT
