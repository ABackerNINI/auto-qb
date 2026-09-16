> 版本: 2026.8.1 | 来源: Context7 MCP | 抓取日期: 2026-09-17

### Instantiate and authenticate qbittorrent-api client

Source: https://qbittorrent-api.readthedocs.io

Instantiate a qbittorrent-api client with connection details and optionally test login credentials. The client automatically handles authentication.

```python
import qbittorrentapi

# instantiate a Client using the appropriate WebUI configuration
conn_info = dict(
    host="localhost",
    port=8080,
    username="admin",
    password="adminadmin",
)
qbt_client = qbittorrentapi.Client(**conn_info)

# the Client will automatically acquire/maintain a logged-in state
# in line with any request. therefore, this is not strictly necessary;
# however, you may want to test the provided login credentials.
try:
    qbt_client.auth_log_in()
except qbittorrentapi.LoginFailed as e:
    print(e)

# if the Client will not be long-lived or many Clients may be created
# in a relatively short amount of time, be sure to log out:
qbt_client.auth_log_out()

# or use a context manager:
with qbittorrentapi.Client(**conn_info) as qbt_client:
    if qbt_client.torrents_add(urls="...") != "Ok.":
        raise Exception("Failed to add torrent.")

# display qBittorrent info
print(f"qBittorrent: {qbt_client.app.version}")
print(f"qBittorrent Web API: {qbt_client.app.web_api_version}")
for k, v in qbt_client.app.build_info.items():
    print(f"{k}: {v}")

# retrieve and show all torrents
for torrent in qbt_client.torrents_info():
    print(f"{torrent.hash[-6:]}: {torrent.name} ({torrent.state})")

# stop all torrents
qbt_client.torrents.stop.all()

```

--------------------------------

### Torrent object methods in qbittorrent-api

Source: https://qbittorrent-api.readthedocs.io

Perform actions directly on torrent objects returned by the client, such as setting location, reannouncing, or modifying upload limits.

```python
import qbittorrentapi
qbt_client = qbittorrentapi.Client(host='localhost:8080', username='admin', password='adminadmin')

for torrent in qbt_client.torrents.info.active():
    torrent.set_location(location='/home/user/torrents/')
    torrent.reannounce()
    torrent.upload_limit = -1

```

--------------------------------

### Direct method calls for qbittorrent-api endpoints

Source: https://qbittorrent-api.readthedocs.io

Interact with qBittorrent Web API endpoints using direct method calls on the client instance. This provides a one-to-one mapping to API endpoints.

```python
import qbittorrentapi
qbt_client = qbittorrentapi.Client(host='localhost:8080', username='admin', password='adminadmin')
qbt_client.app_version()
qbt_client.rss_rules()
qbt_client.torrents_info()
qbt_client.torrents_resume(torrent_hashes='...')
# and so on

```

--------------------------------

### Namespace-based interaction with qbittorrent-api

Source: https://qbittorrent-api.readthedocs.io

Utilize the more robust interface provided by namespaces for interacting with qBittorrent Web API endpoints. This offers a more seamless and intuitive experience.

```python
import qbittorrentapi
qbt_client = qbittorrentapi.Client(host='localhost:8080', username='admin', password='adminadmin')
# changing a preference
is_dht_enabled = qbt_client.app.preferences.dht
qbt_client.app.preferences = dict(dht=not is_dht_enabled)
# stopping all torrents
qbt_client.torrents.stop.all()
# retrieve different views of the log
qbt_client.log.main.warning()
qbt_client.log.main.normal()

```

--------------------------------

### Install qbittorrent-api via pip

Source: https://qbittorrent-api.readthedocs.io

Install the qbittorrent-api package using pip from PyPI.

```bash
python -m pip install qbittorrent-api
```