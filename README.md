# da-project-backend
Data Analytics Project (Backend)

## Prerequisites
1. Install `uv`
    - `uv` is a python package and project manager.
    [Installation steps](https://docs.astral.sh/uv/getting-started/installation/)
2. Get your own [Google Gemini API key](https://ai.google.dev/gemini-api/docs/api-key)

## Setup
1. Create and activate virutal environment

    Windows
    ```bash
    uv venv
    .venv/scripts/activate
    ```
    Linux
    ```bash
    uv venv
    source .venv/bin/activate
    ```

2. Download dependencies

    ```bash
    uv sync
    ```

3. Take the `.env.example` and rename it to `.env`. Assign the
`GOOGLE_API_KEY` in `.env` with the Gemini API key you got earlier
    ```bash
    GOOGLE_API_KEY=YOUR_KEY_HERE
    ```

3. Run server
    ```bash
    fastapi dev da-project-backend/app
    ```

---

Go to [localhost:8000/docs](localhost:8000/docs) to view the API documentation
