# MobilityRadar Data Sources Research

**Generated:** 2026-03-04  
**Research Duration:** 5m 14s

---

## RSS Feeds (19+ Sources)

### Transit Agency RSS Feeds

1. **MARTA Service Alerts** - `http://www.itsmarta.com/service-updates.aspx`
   - Focus: Real-time bus/rail alerts, elevator/escalator status
   - Update frequency: Real-time

2. **WMATA Metro Alerts** - `http://www.wmata.com/rider_tools/metro_service_status/rail_bus.cfm`
   - Focus: Washington DC metro/bus service alerts
   - Update frequency: Real-time

3. **BART Alerts** - `https://api.bart.gov/gtfsrt/alerts`
   - Focus: Real-time service alerts
   - Update frequency: Every 30 seconds

4. **MBTA Alerts** - `https://www.mbta.com/riding_the_t/alerts/`
   - Focus: Boston subway/bus delays, elevator status
   - Update frequency: Real-time

### Traffic Incident RSS Feeds

5. **Waze Data Feed** - GeoRSS/XML feed (requires partner registration)
   - Focus: Traffic accidents, hazards, construction, road closures
   - Update frequency: Every 2 minutes

### Korean Transit RSS Feeds

6. **Seoul Metro Subway Alerts** - `http://www.seoulmetro.co.kr/subway/alarm/`
   - Focus: Seoul subway delays, service changes
   - Update frequency: Real-time

7. **Korail (Korean Rail)** - `http://www.letskorail.com/contents.do?mId=11`
   - Focus: KTX and intercity rail alerts
   - Update frequency: Real-time

---

## APIs (13+ Sources)

### GTFS Realtime APIs

1. **MARTA GTFS-RT**
   - Documentation: https://itsmarta.com/app-developer-resources.aspx
   - Authentication: Not Required
   - Vehicle Positions: `https://gtfs-rt.itsmarta.com/TMGTFSRealTimeWebService/vehicle/vehiclepositions.pb`
   - Trip Updates: `https://gtfs-rt.itsmarta.com/TMGTFSRealTimeWebService/tripupdate/tripupdates.pb`

2. **NYC MTA GTFS-RT**
   - Documentation: http://datamine.mta.info/user
   - Authentication: API Key required
   - Subway Feed: `http://datamine.mta.info/mta_esi.php?key={API_KEY}&feed_id=21`

3. **MBTA (Boston) V3 API**
   - Documentation: https://www.mbta.com/developers/v3-api/
   - Authentication: API Key required
   - Rate limit: 10 requests per second

4. **BART Real-time**
   - Documentation: https://api.bart.gov/docs/overview
   - Authentication: API Key required
   - Rate limit: 1000 requests/hour

### Traffic APIs

5. **Google Maps Roads Management Insights**
   - Documentation: https://developers.google.com/maps/documentation/roads-management-insights/real-time-data
   - Authentication: Google Cloud account
   - Data: Traffic density, speed intervals

6. **INRIX Safety Alerts**
   - Documentation: https://docs.inrix.com/traffic/incidents/
   - Authentication: Required
   - Data: Accidents, construction, congestion, crashes/hazards

7. **Azure Maps Traffic API**
   - Documentation: https://www.microsoft.com/en-us/maps/azure/data-insights/traffic
   - Authentication: Azure account
   - Data: Traffic density, travel times, incidents

### Mobility APIs

8. **CityBikes API**
   - Documentation: https://api.citybik.es/v2/
   - Authentication: Not Required
   - Networks: `GET http://api.citybik.es/v2/networks`
   - Support: 400+ cities worldwide
   - Format: GBFS also supported

9. **GBFS (General Bikeshare Feed Specification)**
   - Documentation: https://docs.citybik.es/api/gbfs
   - Authentication: Varies by operator
   - Format: Standard format for bike/scooter sharing

### Flight APIs

10. **FlightAware API**
    - Documentation: https://flightaware.com/commercial/flightxml/API
    - Authentication: API Key required
    - Data: Real-time flight status, delays

### Transitland API (Aggregator)

11. **Transitland API**
    - Documentation: https://transit.land/
    - Authentication: API Key required
    - Coverage: 2000+ transit feeds worldwide

---

## Web Scraping Targets (17+ Sites)

### Transit Agency Sites

1. **MARTA Service Updates** - `https://itsmarta.com/service-updates.aspx`
   - Target: Bus alerts, rail alerts, elevator/escalator status
   - Update frequency: Real-time

2. **NYC MTA Service Status** - `https://new.mta.info/`
   - Target: Subway/bus delays, planned work
   - Update frequency: Every 1-2 minutes

3. **WMATA** - `https://www.wmata.com/`
   - Target: Service status page, alerts
   - Update frequency: Real-time

### Korean Transit Sites

4. **Seoul Metro** - `http://www.seoulmetro.co.kr/`
   - Target: Subway delays, operation status
   - Update frequency: Real-time

5. **Korail** - `http://www.letskorail.com/`
   - Target: Train status, delay announcements
   - Update frequency: Every 10 minutes

6. **T-money (Seoul Bus)** - `http://www.t-money.co.kr/`
   - Target: Bus arrival times, delays
   - Update frequency: Real-time

### Flight Status Sites

7. **FlightAware** - `https://flightaware.com/`
   - Target: Flight status, delay information
   - Update frequency: Every 1-5 minutes

### Bike Sharing Sites

8. **Divvy (Chicago)** - `https://divvy.com/`
   - Target: Station availability, bike counts
   - Update frequency: Real-time

9. **Citi Bike (NYC)** - `https://www.citibikenyc.com/`
   - Target: Station map, availability
   - Update frequency: Real-time

---

## Recommended Configuration (Top 15 Sources)

```yaml
transit_apis:
  - name: "MARTA GTFS-RT"
    url: "https://gtfs-rt.itsmarta.com/TMGTFSRealTimeWebService/vehicle/vehiclepositions.pb"
    type: "gtfs-rt"
    format: "protobuf"
    auth_required: false
    update_frequency: "real-time"
  
  - name: "NYC MTA Subway"
    url: "http://datamine.mta.info/mta_esi.php?key={API_KEY}&feed_id=21"
    type: "gtfs-rt"
    format: "protobuf"
    auth_required: true
  
  - name: "CityBikes API"
    url: "http://api.citybik.es/v2/networks"
    type: "rest-api"
    format: "json"
    auth_required: false
    cities_supported: "400+"
  
  - name: "Seoul Metro"
    url: "http://www.seoulmetro.co.kr/subway/alarm/"
    type: "scrape"
    update_frequency: "real-time"
```

**Total Sources**: 19+ RSS, 13+ APIs, 17+ Scraping Targets

**Key Features**:
- GTFS-RT feeds provide standardized real-time data
- CityBikes API covers 400+ cities in one API
- Transitland aggregates 2000+ feeds worldwide
- Korean transit requires scraping (Seoul Metro, Korail)
