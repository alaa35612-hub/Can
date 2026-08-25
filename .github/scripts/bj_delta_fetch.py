#!/usr/bin/env python3
import base64, json, random, time, urllib.parse, urllib.request, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

CUTOFF_OPEN = 1787688900000
CUTOFF_CLOSE = 1787689799999
INTERVAL_MS = 900000
KLINE_START = 1787685300000
OI_START_DEFAULT = 1787685300000
OI_START_OVERRIDES = {"BTCU": 1787682600000}
SYMBOLS_Z = "eNpVmN2S3CgMhV8oF5kkVbt7iTG2GWNgAPd05/0fZNXWp55kpopzxK8QksD9fT37PL69fb/+pjL9KR7lq3UqeRfB/yloi3fji28hHP0lLqns8SWlM/uXUEMNr/kQtKW58TVD/0vY4vQag6At98DMMftN2TG56TGXVSf+8fuCX1fp3E3XhkiNN9zAAZ6Ks9MBF4ocWoHcIGuaIQyNdI1ryP2REQyL9WJ4vE/U7KiyIyfTKa30TdHUTcmqasxWx7gcD2ry3pRgZVfjT4g1MKapfRWfsgdtM20/jIDVWoC7YkfuI7wYZLCfUZiLxU8/YsE+Wt6ci8YM76qhkmdNZvgnm7snUB3H/R44x/RDQfwCkuW//3z7QzI6G9mNgM1aengxUPWY1HTTdWoeFDm4426MniGBjXWjL5B12OlNMdHtchUPPmVOaUqho0M6MZgwtfZ0sFjWo1V8ytSXQ2MBIjUtjGHsBinelxT/efv1l7z8ZDLW6oidYcOfV9HnN9CDz0YGjU/FMyXMcJX+v38VLSC8q2C7QYZu1uuMPhANQhpENqJsWUE9BL/i8n4T+67nwwTW2Jhg07zhd5RK4hE4tLfVCjYXi6RA4vDlYKYiKZANFNO36JZ9Kxycv7bkQZHHDrLW6AzV8mbIbh6TKfXQCWfXN8hw16b8F5XaEIzcVbmZCJ/LXO6wVT3jlUSFMHth73MpM8RadP9ziwvs7LqX+TEz8UPjPswhQ1hAQkrRkml4Jk9lqauCIWsqDtnkd7AXI4o1qpUsvEKvpXGdCFfEG8PYlqjzwq668yqe7qvowatRDzGcGp5BktVFFteGLyT6JagVlkVh040ukYtkietGj5iuBRRFTsXvxj4hZ5yNqS2XwqWwlLR3WFP7Lo0cqWuvjvhayVhi2kh4rHFdk6q2Jh29kjhW0tZaSFtrZUxzh5FuVXFZ7I5bG/3bDYKt1xM9Tjpq+RnU7JsLs0tQDnmbrvvFG5Ea6x0OSOQu3w67aTZz081y24Z7bufBxFo+KvHzZBeJngQZfQXVDlGcH6KQNGQjdoo5MhDHxBwx01467WU4I9ak0Ajid9cPTUzvpJX3kNLjKlQsquw7U74PneH9VJ13e4QIGXp7GHvWdXCAXLKS4DJX027ht8ehS+1HZjiPub1gyr2rOyQ3gcAD26ZZR6aXzyd5tDhj+ryEPGv6sDZ6k7LTx9DtJzJL4mpJOFg6D/YtT06nt37iBXa4lbQgDM0PczMh44s1oyxzuFu0Kj3zI6xUBLkYrDHgbEdoCTJiNwYCGthHNAWiLWqndBCGR/G08EQ6JPWGvMJb3ehfCAMhavZjoMUpsePYipYP9bvsSkNBOQ8NNMizJvLWzaHQZPKn6pZfB5pJXvlgME+8TNzle1XjlzWDChnfKLxiS7aGASrUYIT2arJCw0qlzXidME3sEKm5yippOsLuOplMPpMF69O01zBjz7pSrXlzjRtPqGIMt9A67bFW4r7GO8FUJRQgJw4g2g9dRYnUkF0EOZ1aqn1iPe8vZ+2fbFAYBHerTR4f40WN4Bd1aHjW86j2FntySJ4jyz646T44go9x6lwfV9lcC5CbkUdH+xa8S0ZnMNuRtCD9blBA31lyf4A365tUxVamAslYVk6A0ZWl+OhoJ17UbtqzuyVACNju5ASN8toXMjjULp9IeFr33GNCFLl5esAwfVHj9S2w5x5x7x6bTbPTxLdY3x88G4UpJqZJegCdC0Nt6r+ZbV+264Wrr4tJPIxA6aXq6fVq37a9vtSrOyj+tHAL98pyH1iDR7xk4QmvF4ryY2KmId/7sBUs7d0YyLdi55rrpwak4lNGg9Nu4W7lRo9P1/hZod8xOvm8PxqX3XAeXMG4FxifEMNZhcIWvphi1MflIJcPHkMj41riIOg0yicPTbko5B1MO99kowVmtE9neZMc+g43dtVxcwsj3AZf0MNazqae/z+I9RCg"
SYMBOLS = zlib.decompress(base64.b64decode(SYMBOLS_Z)).decode().split(",")
BASES = ["https://fapi.binance.com", "https://fapi1.binance.com", "https://fapi2.binance.com", "https://fapi3.binance.com", "https://fapi4.binance.com"]

assert len(SYMBOLS) == 500

def expected(start):
    return 0 if start > CUTOFF_OPEN else (CUTOFF_OPEN - start) // INTERVAL_MS + 1

def get_json(path, params, retries=7):
    errors = []
    for attempt in range(retries):
        base = BASES[attempt % len(BASES)]
        url = base + path + "?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"BlackJohnDataUpdate/1.0","Accept":"application/json"})
            with urllib.request.urlopen(req, timeout=25) as response:
                return json.loads(response.read().decode("utf-8")), url
        except Exception as exc:
            errors.append(repr(exc))
            time.sleep(min(8.0, 0.5 * (2 ** attempt)) + random.random() * 0.25)
    raise RuntimeError(" | ".join(errors[-3:]))

def fetch_symbol(symbol):
    rec = {"symbol":symbol,"kline":[],"oi":[],"errors":[]}
    try:
        raw, url = get_json("/fapi/v1/klines", {"symbol":symbol,"interval":"15m","startTime":KLINE_START,"endTime":CUTOFF_CLOSE,"limit":expected(KLINE_START)})
        rec["kline"] = [row for row in raw if isinstance(row,list) and len(row)>=11 and KLINE_START <= int(row[0]) <= CUTOFF_OPEN and int(row[6]) <= CUTOFF_CLOSE]
        rec["kline_url"] = url
    except Exception as exc:
        rec["errors"].append({"source":"kline","error":repr(exc)})
    oi_start = OI_START_OVERRIDES.get(symbol, OI_START_DEFAULT)
    try:
        raw, url = get_json("/futures/data/openInterestHist", {"symbol":symbol,"period":"15m","startTime":oi_start,"endTime":CUTOFF_OPEN,"limit":expected(oi_start)})
        rec["oi"] = [row for row in raw if isinstance(row,dict) and oi_start <= int(row.get("timestamp",-1)) <= CUTOFF_OPEN]
        rec["oi_url"] = url
    except Exception as exc:
        rec["errors"].append({"source":"oi","error":repr(exc)})
    return rec

def main():
    result = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_symbol,s):s for s in SYMBOLS}
        for i, future in enumerate(as_completed(futures), 1):
            symbol = futures[future]
            try:
                result[symbol] = future.result()
            except Exception as exc:
                result[symbol] = {"symbol":symbol,"kline":[],"oi":[],"errors":[{"source":"worker","error":repr(exc)}]}
            if i % 25 == 0:
                print(f"{i}/500", flush=True)
    Path("delta_raw.json").write_text(json.dumps(result,separators=(",",":")),encoding="utf-8")
    report = {
        "cutoff_open":CUTOFF_OPEN,"cutoff_close":CUTOFF_CLOSE,"symbols":len(SYMBOLS),
        "kline_rows":sum(len(v.get("kline",[])) for v in result.values()),
        "oi_rows":sum(len(v.get("oi",[])) for v in result.values()),
        "symbols_kline_complete":sum(len(v.get("kline",[])) == expected(KLINE_START) for v in result.values()),
        "symbols_oi_complete":sum(len(v.get("oi",[])) == expected(OI_START_OVERRIDES.get(s,OI_START_DEFAULT)) for s,v in result.items()),
        "symbols_with_errors":sum(bool(v.get("errors")) for v in result.values()),
        "failures":{s:v.get("errors") for s,v in result.items() if v.get("errors")}
    }
    Path("data_update_fetch_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__ == "__main__":
    main()
