# `fmi-cli`

[![build](https://github.com/paasim/fmi-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/paasim/fmi-cli/actions/workflows/ci.yml)

A python library downloading observations and forecasts for weather, solar radiation and air quality from the [FMI API](http://en.ilmatieteenlaitos.fi/open-data-manual).

## Usage

All the APIs have default start and end times (in the near future for forecasts, past for observations), parameter values and resolution but they can be changed. There are also Helsinki-centric defaults for stations (identified by `fmisid`), see [metadata](#Metadata)-section for how to query for different stations.

### Observations

```python
from datetime import datetime, timedelta, UTC
from fmi_cli import get_weather, get_radiation


# Hourly temperature, snow depth (in cm) and relative humidity from Kaisaniemi in January.
fmisid = 100971
start_time = datetime(2025,1,2,1,tzinfo=UTC)
end_time = datetime(2025,1,2,3,tzinfo=UTC)
resolution = timedelta(hours=1)
parameters=["t2m", "snow_aws", "rh"]
wttr = get_weather(fmisid, start_time, end_time, resolution, parameters)
for w in wttr[:6]:
    print(f"{w[1]:<8} at {w[0]} is {w[2]}")


# (Direct) solar radiation from Kumpula at May.
fmisid = 101004
start_time = datetime(2025,5,17,15,tzinfo=UTC)
end_time = datetime(2025,5,17,16,tzinfo=UTC)
resolution = timedelta(minutes=1)
parameters=["dir_1min"]
rad = get_radiation(fmisid, start_time, end_time, resolution, parameters)
for r in rad[:6]:
    print(f"{r[1]} at {r[0]} is {r[2]}")
```


### Forecasts

There are corresponding forecasts for each observation kind (weather, solar radiation and air quality). As weather and solar radiation forecasts are outputs of the same model, by default the `get_weather_forecast` and `get_radiation_forecast` return the same quantities (= observable properties).

```python
from datetime import datetime, timedelta, UTC
from fmi_cli import get_weather_forecast, get_airquality_forecast


# Hourly temperature, wind speed and rain forecast for Kaisaniemi.
fmisid = 100971
parameters=["Temperature", "WindSpeedMS", "PrecipitationAmount"]
wttr = get_weather_forecast(fmisid, parameters=parameters)
for w in wttr[:6]:
    print(f"{w[1]:<19} at {w[0]} is {w[2]}")


# Air quality forecast for Kumpula
fmisid = 101004
aq = get_airquality_forecast(fmisid)
for a in aq[:14]:
    print(f"{a[1]:<19} at {a[0]} is {a[2]}")
```


### Metadata

There are three different kinds of metadata:
* `Stations`, which describe different kinds (`station_kind`) of stations
* `StoredQueries`, which describe the different APIs that are able to be queried
* `ObservableProperties`, which describe the quantities that are returned from different observation / forecast APIs

```python
from fmi_cli import StoredQueries, ObservableProperties, Stations


# Get all the stations
stations = Stations.get()

# List all weather stations that have 'helsinki' in their name
for r in stations.weather("helsinki"):
    print(r)

# All air quality stations
for aq in stations.airquality():
    print(aq)

# All solar radiation stations
for w in stations.radiation():
    print(w)


# Get all the properties available - these are the observed / forecasted quantities available from the APIS.
properties = ObservableProperties.get()

# All forecasted quantities that are related to (solar) radiation
for p in properties.find_matches("radiation", observations=False):
    print(p)

# All properties that are forecasted and end with p1m - ie. monthly averages
for p in properties.find_matches(r"p1m$", forecasts=False)[:10]:
    print(p)


# Get all the available stored queries - essentially a same as an API in this case.
queries = StoredQueries.get()

# All possible forecast queries
for q in queries.find_matches("forecast")[:8]:
    print(q)

# List all queries that use MEPS and return results in "simple" format.
for q in queries.find_matches("meps.*simple"):
    print(q)
```
