> 版本: 0.28.1 | 来源: Context7 MCP | 抓取日期: 2026-09-17

### httpx.AsyncClient

Source: https://github.com/encode/httpx/blob/master/docs/api.md

AsyncClient class for asynchronous HTTP requests with HTTP/2 and connection pooling support. Provides async request execution and session configuration.

```APIDOC
## class httpx.AsyncClient

### Description
Asynchronous client instance providing connection pooling, HTTP/2 support, and session configuration.

### Members and Methods
- `headers`
- `cookies`
- `params`
- `auth`
- `def request(...)`
- `def get(...)`
- `def head(...)`
- `def options(...)`
- `def post(...)`
- `def put(...)`
- `def patch(...)`
- `def delete(...)`
- `def stream(...)`
- `def build_request(...)`
- `def send(...)`
- `def aclose()`
```

--------------------------------

### httpx.Client

Source: https://github.com/encode/httpx/blob/master/docs/api.md

Client class for sending HTTP requests with HTTP/2 and connection pooling support. Provides synchronous request execution and session configuration.

```APIDOC
## class httpx.Client

### Description
Client instance providing connection pooling, HTTP/2 support, and session configuration for making HTTP requests.

### Members and Methods
- `headers`
- `cookies`
- `params`
- `auth`
- `def request(...)`
- `def get(...)`
- `def head(...)`
- `def options(...)`
- `def post(...)`
- `def put(...)`
- `def patch(...)`
- `def delete(...)`
- `def stream(...)`
- `def build_request(...)`
- `def send(...)`
- `def close()`
```

--------------------------------

### Configure default timeout on httpx.Client

Source: https://github.com/encode/httpx/blob/master/docs/advanced/timeouts.md

Set a default timeout duration across all requests made by an httpx.Client instance, or disable client defaults with timeout=None.

```python
client = httpx.Client()              # Use a default 5s timeout everywhere.
client = httpx.Client(timeout=10.0)  # Use a default 10s timeout everywhere.
client = httpx.Client(timeout=None)  # Disable all timeouts by default.
```

--------------------------------

### Share Custom Headers Across Requests in httpx.Client

Source: https://github.com/encode/httpx/blob/master/docs/advanced/clients.md

Applies configuration such as default headers to every outgoing request by passing them to the Client constructor.

```pycon
>>> url = 'http://httpbin.org/headers'
>>> headers = {'user-agent': 'my-app/0.0.1'}
>>> with httpx.Client(headers=headers) as client:
...     r = client.get(url)
...
>>> r.json()['headers']['User-Agent']
'my-app/0.0.1'
```

--------------------------------

### Catch all request and status errors using httpx.HTTPError

Source: https://github.com/encode/httpx/blob/master/docs/quickstart.md

Uses the base HTTPError class to catch both failed network requests and 4xx/5xx response status errors.

```python
try:
    response = httpx.get("https://www.example.com/")
    response.raise_for_status()
except httpx.HTTPError as exc:
    print(f"Error while requesting {exc.request.url!r}.")

```