
import websockets
import asyncio, json
import logging

logger = logging.getLogger(__name__)

class Extension:
    uri = "ws://localhost:8876"

    def __init__(self, guid=None):
        self.requestServers = {}
        self.events = {}
        self.sid = -1
        self.ridcount = 0
        self.guid = guid

    def _nextrid(self):
        self.ridcount += 1
        return self.ridcount

    async def connect(self):
        ''' Call this to connect to platform.bible '''
        self.ws = await websockets.connect(self.uri)
        initresponse = await self.ws.recv()
        initinfo = json.loads(initresponse)
        self.sid = initinfo['connectorInfo']['clientId']
        self.cguid = initinfo['clientGuid']
        if self.guid:
            self.events["network:onDidClientConnect"] = self.clientConnected
            self.events["network:onDidClientDisconnect"] = self.clientDisconnected
            msg = { "type": "client-connect",
                    "senderId": self.sid,
                    "reconnectingClientGuid": self.guid }
            await self.send(msg)

    def clientConnected(self, obj):
        ''' Callback when receiving the onDidClientConnect event '''
        logger.debug("Establishing connection")
        return True

    async def clientDisconnected(self, obj):
        ''' Callback when receiving the onDidClientDisconnect event '''
        logger.debug("Closing connection")
        await self.ws.close()

    async def recv(self, timeout=None):
        ''' Wait for a message from platform.bible, with or without timeout '''
        if timeout is None:
            res = await self.ws.recv()
        else:
            res = await asyncio.wait_for(self.ws.recv(), timeout)
            if isinstance(res, asyncio.TimeoutError):
                return None
        logger.debug("<<< " + res)
        return json.loads(res)

    async def send(self, obj):
        ''' Send an object to platform.bible '''
        res = json.dumps(obj)
        logger.debug(">>> " + res)
        await self.ws.send(res)

    async def close(self):
        ''' Close the connection, cleaning up registrations first '''
        for k in list(self.requestServers.keys()):
            await self.request("server:unregisterRequest", contents=[k, self.sid], response=True)
            del self.requestServers[k]
        await self.ws.close()

    async def _dofn(self, fn, obj):
        if asyncio.iscoroutine(fn):
            res = await fn(obj)
        else:
            res = fn(obj)
        return res

    async def despatch(self, obj):
        ''' Do something sensible with a received object '''
        if 'requestType' in obj:
            fn = self.requestServers.get(obj['requestType'], None)
            if fn is not None:
                res = await self._dofn(fn, obj)
                if res is not None:
                    await self.response(obj['requestType'], obj['requestId'], obj['senderId'], contents=res)
        elif obj["type"] == "event":
            fn = self.events.get(obj["eventType"], None)
            if fn is not None:
                res = await self._dofn(fn, obj)
                logger.debug(f"{obj['eventType']}: {res}")

    async def registerRequest(self, request, procfn):
        ''' Register a request server '''
        contents = [request, self.sid]
        res = await self.request("server:registerRequest", contents=contents, response=True)
        if res['success']:
            self.requestServers[request] = procfn

    async def request(self, request, contents=[], rid=None, response=False, timeout=None):
        ''' Make a request, and perhaps wait for a response '''
        if rid is None:
            rid = self._nextrid()
        req = { "type": "request",
                "requestType": request,
                "requestId": rid,
                "senderId": self.sid,
                "contents": contents }
        await self.send(req)
        while response:
            res = await self.recv(timeout)
            if res is None:
                return None
            elif res['type'] == 'response'  and res['requestType'] == request \
                                            and res['requestId'] == rid \
                                            and res['requesterId'] == self.sid:
                return res
            else:
                await self.despatch(res)
        return None

    async def response(self, request, rid, sid, contents):
        ''' Send a request response back to platform.bible '''
        req = { "type": "response",
                "requestType": request,
                "requestId": rid,
                "requesterId": sid,
                "senderId": self.sid,
                "contents": contents }
        await self.send(req)
