"""API wrapper for generating the XML envelope and fetching data from the Darwin API"""
import aiohttp
import async_timeout

from .apidata import ApiData


class Api:
    """API wrapper for generating the XML envelope and fetching data from the Darwin API"""

    def __init__(self, api_key, station, destination, request_url, soap_action):
        self.api_key = api_key
        self.request_url = request_url
        self.soap_action = soap_action
        self.time_offset = 0
        self.time_window = 120
        self.station = station
        self.filters = [destination]
        self.data = ApiData()

    def set_config(self, key, val):
        """Set config item, such as time_offset and time_window"""
        if key == "time_offset":
            self.time_offset = val
            return True

        if key == "time_window":
            self.time_window = val
            return True

    def generate_filter_list(self):
        """Generate XML Destination Filters"""
        stations = self.filters
        payload = ""

        for station in stations:
            if station is not None:
                payload += f"<ldb:crs>{station}</ldb:crs>\n"

        return payload

    def generate_data(self):
        """Generate XML SOAP Envelope"""
        api_key = self.api_key
        station = self.station
        time_offset = self.time_offset
        time_window = self.time_window
        filters = self.generate_filter_list()

        data = """<x:Envelope
            xmlns:x="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:ldb="http://thalesgroup.com/RTTI/2016-02-16/ldb/"
            xmlns:ns2="http://thalesgroup.com/RTTI/2010-11-01/ldb/commontypes">
                <x:Header>
                    <ns2:AccessToken>
                        <ns2:TokenValue>{}</ns2:TokenValue>
                    </ns2:AccessToken>
                </x:Header>
                <x:Body>
                    <ldb:GetNextDeparturesWithDetailsRequest>
                        <ldb:crs>{}</ldb:crs>
                        <ldb:filterList>
                            {}
                        </ldb:filterList>
                        <ldb:timeOffset>{}</ldb:timeOffset>
                        <ldb:timeWindow>{}</ldb:timeWindow>
                    </ldb:GetNextDeparturesWithDetailsRequest>
                </x:Body>
            </x:Envelope>""".format(
            api_key, station, filters, time_offset, time_window
        )

        return data

    async def api_request(self):
        """
        To minimise multiple API calls, check if a request from another entity in this component is already in progress.
        If no request is running, generate SOAP Envelope and submit request to Darwin API.
        Otherwise, wait until the existing one is complete, and return that value.
        """
        data = self.generate_data()
        return await self.request(self.request_url, self.soap_action, data)

    async def fetch(self, session, url, soapaction, payload):
        """Fetch data from the Darwin API"""
        try:
            with async_timeout.timeout(15):
                async with session.post(
                    url,
                    headers={
                        "Content-Type": "text/xml",
                        "charset": "utf-8",
                        "SOAPAction": soapaction,
                    },
                    data=payload,
                ) as response:
                    result = await response.text()
                    if result:
                        self.data.populate(result)

                    return result
        except:
            pass

    async def request(self, url, soapaction, data):
        """Prepare core request"""
        async with aiohttp.ClientSession() as session:
            return await self.fetch(session, url, soapaction, data)
