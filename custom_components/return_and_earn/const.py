DOMAIN = "return_and_earn"

API_LOCATIONS_URL = "https://api.au.prod.tomra.cloud/mytomra/v1.0/locations/AU-NSW?includeExternal=true"
API_DETAIL_URL = "https://api.au.prod.tomra.cloud/mytomra/v1.0/locations/details/{uuid}"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

API_HEADERS = {
    "Accept": "application/vnd.api+json",
    "Origin": "https://returnandearn-app.com",
    "Referer": "https://returnandearn-app.com/",
    "User-Agent": "HomeAssistant/return_and_earn",
    "tomra-app-context": "RETURNANDEARN",
}

NOMINATIM_HEADERS = {
    "User-Agent": "HomeAssistant/return_and_earn",
    "Accept-Language": "en",
}

CONF_LOCATION_UUID = "location_uuid"
CONF_LOCATION_NAME = "location_name"
CONF_POLL_INTERVAL = "poll_interval"
CONF_SEARCH_METHOD = "search_method"
CONF_SEARCH_ADDRESS = "search_address"

SEARCH_METHOD_HOME = "near_home"
SEARCH_METHOD_ADDRESS = "near_address"
SEARCH_METHOD_UUID = "manual_uuid"

DEFAULT_POLL_INTERVAL = 15
NEARBY_RESULTS = 20

STATUS_OPEN = "OPEN"
STATUS_SEMI_FULL = "SEMI_FULL"
STATUS_FULL = "FULL"
STATUS_CLOSED = "CLOSED"

OVERALL_OPEN = "Open"
OVERALL_ALMOST_FULL = "Almost Full"
OVERALL_FULL = "Full"
OVERALL_CLOSED = "Closed"
OVERALL_UNKNOWN = "Unknown"
