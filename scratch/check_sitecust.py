import asyncio
import httpx

async def test():
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8765/api/v1', timeout=30.0) as client:
        code = """import io, _io
print("io.open:", io.open)
print("_io.open:", _io.open)
print("FileIO:", _io.FileIO)
"""
        res = await client.post('/execution/run', json={
            'session_id': 'debug-sitecust-6',
            'code': code
        }, headers={'X-Guest-Token': 'test-guest-cust'})
        resp = res.json()
        print("RESP:", resp)

asyncio.run(test())
