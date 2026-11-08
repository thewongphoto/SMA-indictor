"""Verify/cache the pinned OpenSSL sources before kivy-ios can use legacy HTTP.

The official tag's immutable commit snapshot avoids the failing release-download
redirect. Its SHA-256 is separate from the original released tarball; a trusted
existing release archive can be reused without changing toolchain build state.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]


def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda:source.read(131072),b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_copy(source,target):
    with tempfile.NamedTemporaryFile(dir=target.parent,prefix=".openssl-",delete=False) as output:
        temporary=Path(output.name)
    try:
        with Path(source).open("rb") as stream,temporary.open("wb") as output:
            shutil.copyfileobj(stream,output)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def ensure_native_sources(cache,source=None,opener=None,wait=None):
    source=source or json.loads((ROOT/"ios/native-sources.json").read_text())["openssl"]
    opener=opener or urlopen
    wait=wait or time.sleep
    cache=Path(cache)
    cache.mkdir(parents=True,exist_ok=True)
    accepted={source["sha256"],source["released_archive_sha256"]}
    targets=[cache/name for name in source["cache_files"]]
    valid={path:sha256(path) for path in targets if path.is_file()}
    valid={path:digest for path,digest in valid.items() if digest in accepted}
    downloaded=None
    if not valid:
        if not source["url"].startswith("https://"):
            raise RuntimeError("Native sources must use verified HTTPS.")
        with tempfile.NamedTemporaryFile(dir=cache,prefix=".openssl-",delete=False) as output:
            downloaded=Path(output.name)
        try:
            for attempt in range(3):
                try:
                    request=Request(source["url"],headers={"User-Agent":"SMA-iOS-source-preflight"})
                    with opener(request,timeout=60) as response,downloaded.open("wb") as output:
                        shutil.copyfileobj(response,output)
                    break
                except (URLError,TimeoutError,ConnectionError) as error:
                    if isinstance(error,HTTPError) and error.code not in (408,429,500,502,503,504):
                        raise
                    if attempt==2:
                        raise RuntimeError("OpenSSL source download failed after three HTTPS attempts.") from error
                    wait(2**attempt)
            if sha256(downloaded)!=source["sha256"]:
                raise RuntimeError("OpenSSL source checksum mismatch; no unverified archive was installed.")
            for path in targets:
                atomic_copy(downloaded,path)
        finally:
            downloaded.unlink(missing_ok=True)
    else:
        # Keep each valid archive unchanged: its extraction root may already be
        # recorded in a partially completed toolchain build.
        existing=next(iter(valid))
        for path in targets:
            if path not in valid:
                atomic_copy(existing,path)
    result={"version":source["version"],"commit":source["commit"],
            "cache":{path.name:sha256(path) for path in targets}}
    print("Verified OpenSSL native sources: "+json.dumps(result,sort_keys=True))
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache",type=Path)
    args=parser.parse_args()
    ensure_native_sources(args.cache)
