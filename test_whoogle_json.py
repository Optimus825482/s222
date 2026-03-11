"""Test Whoogle JSON API."""
import httpx
import asyncio
import json

WHOOGLE = "http://whoogle-e4s8oc4kkc8sokcsco808ccw.77.42.68.4.sslip.io"

async def test():
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
        # First get session cookie
        await c.get(WHOOGLE)
        print("Cookies:", list(dict(c.cookies).keys()))
        
        # Then search with JSON format
        resp = await c.get(f"{WHOOGLE}/search", params={"q": "openai", "format": "json"})
        d = resp.json()
        print("Keys:", list(d.keys()))
        print("Query:", d.get("query"))
        results = d.get("results", [])
        print(f"Results: {len(results)}")
        if results:
            print("Result keys:", list(results[0].keys()))
            for r in results[:6]:
                print(f"\n  title: {str(r.get('title',''))[:80]}")
                print(f"  href: {str(r.get('href', ''))[:250]}")
                print(f"  text: {str(r.get('text', ''))[:250]}")
                print(f"  content: {str(r.get('content', ''))[:300]}")
        else:
            print("Raw response:", json.dumps(d, indent=2)[:1000])

asyncio.run(test())
