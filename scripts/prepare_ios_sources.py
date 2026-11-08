"""Prepare verified OpenSSL and GitHub source caches for the iPhone build."""
import argparse
import json
from pathlib import Path
from .source_fetch import ensure_verified_source,sha256

ROOT=Path(__file__).resolve().parents[1]


def ensure_native_sources(cache,source=None,opener=None,wait=None):
    source=source or json.loads((ROOT/"ios/native-sources.json").read_text())["openssl"]
    spec=dict(source,accepted_cache_sha256=[source["released_archive_sha256"]])
    return ensure_verified_source(cache,spec,opener,wait)


def prepare_ios_sources(cache):
    from .native_archives import prepare_platform_sources
    result=ensure_native_sources(cache)
    prepare_platform_sources("ios",cache,cache)
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache",type=Path)
    args=parser.parse_args()
    prepare_ios_sources(args.cache)
