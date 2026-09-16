> 版本: 0.53.0 | 来源: Context7 MCP | 抓取日期: 2026-09-17

### Run Uvicorn with Command Line Options

Source: https://uvicorn.dev/settings

Use command line options when running Uvicorn directly to specify host and port.

```bash
uvicorn main:app --host 0.0.0.0 --port 8000

```

--------------------------------

### Run Uvicorn Programmatically

Source: https://uvicorn.dev/settings

Use keyword arguments when running programmatically with `uvicorn.run()` to specify host and port.

```python
uvicorn.run("main:app", host="0.0.0.0", port=8000)

```

--------------------------------

### Run Uvicorn for local development

Source: https://uvicorn.dev/deployment

Executes the application with auto-reloading enabled on a specified port.

```bash
$ uvicorn main:app --reload --port 5000
```

--------------------------------

### Run Uvicorn with Built-in Workers

Source: https://uvicorn.dev/deployment

Use the --workers option to spawn multiple worker processes.

```bash
$ uvicorn main:app --workers 4
```

--------------------------------

### Use Application Factories

Source: https://uvicorn.dev/

Defining an application factory function and running it with the --factory flag.

```python
def create_app():
    app = ...
    return app
```

```bash
uvicorn --factory main:create_app
```