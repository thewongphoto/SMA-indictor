"""Verified HTTPS source caching shared by the mobile build preflights."""
import hashlib
import http.client
import json
from pathlib import Path
import shutil
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda:source.read(131072),b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_copy(source,target):
    target=Path(target)
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent,prefix=".source-",delete=False) as output:
        temporary=Path(output.name)
    try:
        with Path(source).open("rb") as stream,temporary.open("wb") as output:
            shutil.copyfileobj(stream,output)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def ensure_verified_source(cache,source,opener=None,wait=None):
    opener=opener or urlopen
    wait=wait or time.sleep
    cache=Path(cache)
    cache.mkdir(parents=True,exist_ok=True)
    accepted={source["sha256"],*source.get("accepted_cache_sha256",[])}
    targets=[cache/name for name in source["cache_files"]]
    valid={path:sha256(path) for path in targets if path.is_file()}
    valid={path:digest for path,digest in valid.items() if digest in accepted}
    if not valid:
        if not source["url"].startswith("https://"):
            raise RuntimeError("Native sources must use verified HTTPS.")
        with tempfile.NamedTemporaryFile(dir=cache,prefix=".source-",delete=False) as output:
            downloaded=Path(output.name)
        try:
            for attempt in range(3):
                try:
                    request=Request(source["url"],headers={"User-Agent":"SMA-native-source-preflight"})
                    with opener(request,timeout=90) as response,downloaded.open("wb") as output:
                        shutil.copyfileobj(response,output)
                    break
                except (URLError,TimeoutError,ConnectionError,http.client.IncompleteRead) as error:
                    if isinstance(error,HTTPError) and error.code not in (408,429,500,502,503,504):
                        raise
                    if isinstance(error,HTTPError) and error.code==429 and error.headers.get("Retry-After"):
                        # Do not retry earlier than a server-specified pause.
                        raise RuntimeError("Source server rate limited this request. Retry after its Retry-After interval.") from error
                    if attempt==2:
                        raise RuntimeError("Native source download failed after three HTTPS attempts.") from error
                    wait(2**attempt)
            if sha256(downloaded)!=source["sha256"]:
                raise RuntimeError("Native source checksum mismatch; no unverified archive was installed.")
            for path in targets:
                atomic_copy(downloaded,path)
        finally:
            downloaded.unlink(missing_ok=True)
    else:
        # Preserve valid legacy archives and their existing extraction roots.
        existing=next(iter(valid))
        for path in targets:
            if path not in valid:
                atomic_copy(existing,path)
    result={"version":source["version"],"commit":source["commit"],
            "cache":{path.name:sha256(path) for path in targets}}
    print("Verified native source: "+json.dumps(result,sort_keys=True),flush=True)
    return result
