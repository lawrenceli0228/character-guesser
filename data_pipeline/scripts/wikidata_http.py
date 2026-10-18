"""Small HTTP helpers shared by the scripts that talk to Wikidata/Wikimedia.

- sparql(): Wikidata Query Service (WDQS), good for facts about a known list of IDs.
- qlever(): the QLever Wikidata endpoint, fast for whole-database rankings that
  time out on WDQS (e.g. "all humans by number of sitelinks").
- get_json(): plain GET for REST APIs such as Wikimedia pageviews.
"""

import http.client
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

WDQS_ENDPOINT = "https://query.wikidata.org/sparql"
QLEVER_ENDPOINT = "https://qlever.dev/api/wikidata"
USER_AGENT = "COMP9001-character-guesser/0.1 (educational student project)"
MAX_ATTEMPTS = 5
RETRY_DELAY_SECONDS = 10

QLEVER_PREFIXES = """
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <http://schema.org/>
"""


def _open_json(request, timeout):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            # Only rate limits and server errors are worth retrying.
            if error.code != 429 and error.code < 500 or attempt == MAX_ATTEMPTS:
                raise RuntimeError("request failed: HTTP %d for %s" % (error.code, request.full_url[:120])) from error
            print("  HTTP %d; retrying..." % error.code, file=sys.stderr)
            time.sleep(RETRY_DELAY_SECONDS * attempt)
        except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as error:  # truncated replies
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError("request failed after retries: %s" % error) from error
            print("  request failed (%s); retrying..." % error, file=sys.stderr)
            time.sleep(RETRY_DELAY_SECONDS * attempt)
    raise AssertionError("unreachable")


def sparql(query, timeout=90):
    """Run a query on WDQS and return the list of result bindings."""
    params = urllib.parse.urlencode({"query": query, "format": "json"})
    request = urllib.request.Request(
        WDQS_ENDPOINT, data=params.encode("utf-8"),
        headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
    )
    return _require(_open_json(request, timeout), request)["results"]["bindings"]


def _require(data, request):
    if data is None:
        raise RuntimeError("query endpoint returned 404 for %s" % request.full_url[:120])
    return data


def qlever(query, timeout=180):
    """Run a query (prefixes added automatically) on QLever and return the bindings."""
    url = QLEVER_ENDPOINT + "?" + urllib.parse.urlencode({"query": QLEVER_PREFIXES + query})
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
    )
    return _require(_open_json(request, timeout), request)["results"]["bindings"]


def get_json(url, timeout=30):
    """GET a JSON document; returns None for 404."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    return _open_json(request, timeout)


def value(binding, key, default=""):
    return binding.get(key, {}).get("value", default)


def entity_id(uri):
    return uri.rsplit("/", 1)[-1]


def chunks(items, size):
    items = list(items)
    for start in range(0, len(items), size):
        yield items[start:start + size]
