"""Pack a NOAA NCSS subset into yearly month/latitude/longitude grids."""
import sys
from pathlib import Path

import netCDF4
import numpy as np

with netCDF4.Dataset(sys.argv[1]) as src:
    assert list(src["lat"][:]) == list(range(33, 86))
    assert list(src["lon"][:]) == list(range(15, 195))
    assert src["air"].dimensions == ("time", "lat", "lon") and src["air"].units == "degK"
    dates = netCDF4.num2date(src["time"][:], src["time"].units)
    first,last=dates[0].year,dates[-1].year
    assert first >= 1900 and last < 1940 and len(dates)==12*(last-first+1)
    for year in range(first, last+1):
        start = (year - first) * 12
        assert all(d.year == year and d.month == i+1 for i,d in enumerate(dates[start:start+12]))
        celsius = src["air"][start:start+12] - 273.15
        assert not np.ma.getmaskarray(celsius).any() and np.isfinite(celsius).all(), "Incomplete monthly grid"
        half_degrees = np.ma.round(celsius * 2)
        assert half_degrees.min() >= -128 and half_degrees.max() < 127
        (Path(__file__).parent / f"{year}.bin").write_bytes(half_degrees.filled(127).astype("int8").tobytes())
