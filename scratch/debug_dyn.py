import asyncio
import httpx

async def test():
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8765/api/v1', timeout=30.0) as client:
        # Obfuscated string so static regex doesn't match
        code = """p = "".join([chr(46), chr(46), "/", "user", "_admin", "_super", "/default/Sales Dataset.csv"])
try:
    with open(p) as f:
        print("LEAK:", f.read())
except PermissionError as e:
    print("RUNTIME_GUARD_CAUGHT:", str(e))
except Exception as e:
    print("OTHER_ERR:", type(e).__name__, str(e))
"""
        res = await client.post('/execution/run', json={
            'session_id': 'dyn-test-fresh',
            'code': code
        }, headers={'X-Guest-Token': 'test-guest-fresh'})
        print("STATUS:", res.status_code)
        resp = res.json()
        print("OUTPUTS:")
        for o in resp.get("outputs", []):
            print(o.get("text"))

asyncio.run(test())

