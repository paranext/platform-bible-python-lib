#!/usr/bin/python3

import sys, os, unittest
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from platformbible.platform import Extension

extension_guid = "87e927f1-d381-4574-819f-a69c9abfb5d0"

class Basic(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.extension = Extension(guid=extension_guid)
        await self.extension.connect()

    async def asyncTearDown(self):
        await self.extension.close()

    # @unittest.skip("Just try one")
    async def test_echo(self):
        teststr = "Hello Platform.Bible"
        res = await self.extension.request("command:test.echo", [teststr], response=True)
        self.assertEqual(res['contents'], teststr)

    async def test_register(self):
        testcommand = "command:mhtest.count"
        teststr = "Hello World"
        results = []

        # Note this callback doesn't have to be async (unless it calls an async fn)
        def dotestcmd(obj):
            results.append(obj['contents'])
            return [len(obj['contents'][0])]

        await self.extension.registerRequest(testcommand, dotestcmd)
        res = await self.extension.request(testcommand, [teststr], response=True)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0][0], teststr)
        self.assertEqual(res['contents'][0], len(teststr))

if __name__ == "__main__":
    unittest.main()

