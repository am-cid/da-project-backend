# da-project-backend
Data Analytics Project (Backend)

## Prerequisite: Install `uv`
`uv` is a python package and project manager. [Installation steps](https://docs.astral.sh/uv/getting-started/installation/)

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

3. Run server
    ```bash
    fastapi dev da-project-be/app
    ```

---
*sample request*
```bash
curl -X 'GET' \
  'localhost:8000/' \
  -H 'accept: application/json'
```
should return
```
{"hello":"world"}
