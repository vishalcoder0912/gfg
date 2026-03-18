"""Quick integration test for Gemini-powered dashboard generation."""
import requests
import json

BASE = "http://localhost:8000"

# Test 1: Generate Dashboard
print("=" * 60)
print("TEST 1: Generate Dashboard (show me total sales by region)")
print("=" * 60)
r = requests.post(
    f"{BASE}/api/generate-dashboard",
    json={"dataset_id": "demo_sales", "prompt": "show me total sales by region"},
)
data = r.json()
d = data.get("dashboard", {})
print("Status:", r.status_code)
print("Title:", d.get("title", ""))
print("Num Charts:", len(d.get("charts", [])))

for i, c in enumerate(d.get("charts", [])):
    title = c.get("title", "")
    ctype = c.get("chartType", "")
    rows = len(c.get("data", []))
    xk = c.get("xKey", "")
    yk = c.get("yKeys", [])
    print(f"  Chart {i+1}: {title} | type: {ctype} | rows: {rows} | xKey: {xk} | yKeys: {yk}")
    # Show first 2 data rows
    for row in c.get("data", [])[:2]:
        print(f"    Sample: {row}")

print("Insights:", d.get("insights", []))
print("Summary Cards:", [(sc.get("label"), sc.get("value")) for sc in d.get("summary_cards", [])])
print("Warnings:", data.get("warnings", []))
session_id = data.get("session_id", "")
print("Session ID:", session_id)

# Test 2: Follow-up
if session_id:
    print()
    print("=" * 60)
    print("TEST 2: Follow-up (show it as a pie chart)")
    print("=" * 60)
    r2 = requests.post(
        f"{BASE}/api/follow-up",
        json={"session_id": session_id, "prompt": "show it as a pie chart"},
    )
    data2 = r2.json()
    d2 = data2.get("dashboard", {})
    print("Status:", r2.status_code)
    print("Title:", d2.get("title", ""))
    print("Num Charts:", len(d2.get("charts", [])))
    print("Warnings:", data2.get("warnings", []))
    for i, c in enumerate(d2.get("charts", [])):
        title = c.get("title", "")
        ctype = c.get("chartType", "")
        rows = len(c.get("data", []))
        print(f"  Chart {i+1}: {title} | type: {ctype} | rows: {rows}")

# Test 3: Another query
print()
print("=" * 60)
print("TEST 3: Generate Dashboard (top 5 products by revenue)")
print("=" * 60)
r3 = requests.post(
    f"{BASE}/api/generate-dashboard",
    json={"dataset_id": "demo_sales", "prompt": "top 5 products by revenue"},
)
data3 = r3.json()
d3 = data3.get("dashboard", {})
print("Status:", r3.status_code)
print("Title:", d3.get("title", ""))
print("Num Charts:", len(d3.get("charts", [])))
for i, c in enumerate(d3.get("charts", [])):
    title = c.get("title", "")
    ctype = c.get("chartType", "")
    rows = len(c.get("data", []))
    print(f"  Chart {i+1}: {title} | type: {ctype} | rows: {rows}")
    for row in c.get("data", [])[:3]:
        print(f"    Sample: {row}")
print("Insights:", d3.get("insights", []))
print("Warnings:", data3.get("warnings", []))

print()
print("=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
