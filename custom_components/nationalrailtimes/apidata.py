"""Data handler for the response from the Darwin API"""
from datetime import datetime, timedelta
from dateutil import parser
import xmltodict
import re


def check_key(element, *keys):
    """
    Check if *keys (nested) exists in `element` (dict).
    """
    if not isinstance(element, dict):
        raise AttributeError("keys_exists() expects dict as first argument.")
    if len(keys) == 0:
        raise AttributeError("keys_exists() expects at least two arguments, one given.")

    _element = element
    for key in keys:
        try:
            _element = _element[key]
        except KeyError:
            return False
    return True


class ApiData:
    """Data handler class for the response from the Darwin API"""

    def __init__(self):
        self.raw_result = ""
        self._last_update = None
        self._api_xml = []
        self._station_name = ""
        self._refresh_interval = 2

    def populate(self, xml_data):
        """Hydrate the data entity with the XML API response"""
        self.raw_result = xml_data
        self._api_xml = []
        self._last_update = datetime.now()

    # def is_data_stale(self):
    #     """Check if the data hydration is stale and requires refreshing"""
    #     if len(self.raw_result) > 0:
    #         now = datetime.now()
    #         stale_time = self._last_update + timedelta(minutes=self._refresh_interval)

    #         if stale_time < now:
    #             return False

    #     return True

    def get_data(self):
        """Parse the XML raw data and convert into a usable dictionary"""
        if self.raw_result:
            if not self._api_xml:
                formatted = re.sub(r"lt[0-9]\:", "", self.raw_result)
                data = xmltodict.parse(formatted)
                if data and check_key(
                    data,
                    "soap:Envelope",
                    "soap:Body",
                    "GetNextDeparturesWithDetailsResponse",
                    "DeparturesBoard",
                ):
                    self._api_xml = data["soap:Envelope"]["soap:Body"][
                        "GetNextDeparturesWithDetailsResponse"
                    ]["DeparturesBoard"]
            return self._api_xml

    def is_empty(self):
        """Check if the entity is empty"""
        return len(self._api_xml) == 0

    def get_destination_data(self, station):
        """Get the destination data"""
        data = self.get_data()
        if data and check_key(data, "departures"):
            destinations = data["departures"]["destination"]
            if destinations:
                if isinstance(destinations, dict):
                    if destinations["@crs"] == station:
                        service = destinations["service"]
                        if check_key(service, "serviceType"):
                            return service
                else:
                    for destination in destinations:
                        if destination["@crs"] == station:
                            service = destination["service"]
                            if check_key(service, "serviceType"):
                                return service

    def get_service_details(self, crx):
        """Get the destinations service details data"""
        data = self.get_destination_data(crx)
        if data:
            cloned_data = data.copy()
            del cloned_data["subsequentCallingPoints"]
            return cloned_data

    def get_calling_points(self, crx):
        """Get the stations the service stops at on route to the destination"""
        data = self.get_destination_data(crx)
        if data:
            return data["subsequentCallingPoints"]["callingPointList"]["callingPoint"]

    def get_station_name(self):
        """Get the name of the station to watch for departures"""
        if not self._station_name:
            data = self.get_data()
            if data:
                name = data["locationName"]
                if name:
                    self._station_name = name

        return self._station_name

    def get_destination_name(self, crx):
        """Get the name of the final destination station"""
        data = self.get_destination_data(crx)
        if data:
            if check_key(data, "destination"):
                return data["destination"]["location"]["locationName"]

    def message(self):
        """Check for any station messages, such as cancelations, lack of service etc"""
        data = self.get_data()
        if check_key(data, "nrccMessages"):
            messages = data["nrccMessages"]
            if check_key(messages, "message"):
                return re.sub(
                    r"this station",
                    self.get_station_name() + " station",
                    messages["message"],
                )

    def get_last_update(self):
        """Get the time the data was populated"""
        return self._last_update

    def get_state(self, crx):
        """Get the state of the data based on destination"""
        data = self.get_service_details(crx)
        if data:
            return parser.parse(data["std"]).strftime("%H:%M")
        return "None"
