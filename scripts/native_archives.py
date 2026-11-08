"""Pinned GitHub source archives and adapters for both mobile toolchains."""
import json
from pathlib import Path
import re
from urllib.parse import urlsplit,urlunsplit

from .source_fetch import atomic_copy,ensure_verified_source,sha256

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"scripts/native-archives.json"


def source_specs():
    return json.loads(MANIFEST.read_text())["sources"]


def direct_archive_url(url):
    """Use GitHub's archive server directly; retain recipe filenames/digests."""
    parts=urlsplit(url)
    if parts.scheme!="https" or parts.netloc!="github.com" or parts.query:
        return url
    match=re.fullmatch(r"/([^/]+)/([^/]+)/archive/(.+)\.(tar\.gz|zip)",parts.path)
    if not match:
        return url
    owner,repo,ref,kind=match.groups()
    return urlunsplit(("https","codeload.github.com",f"/{owner}/{repo}/{kind}/{ref}","",parts.fragment))


def known_source(url,specs):
    if not url:
        return None
    plain=urlsplit(url)._replace(fragment="").geturl()
    return next((spec for spec in specs if plain in (spec["source_url"],spec["url"])),None)


def ensure_archive(cache,spec):
    ensure_verified_source(cache,dict(spec,cache_files=[spec["filename"]]))
    return Path(cache)/spec["filename"]


def prepare_platform_sources(platform,destination,cache,specs=None):
    destination,cache=Path(destination),Path(cache)
    prepared=[]
    for spec in (source_specs() if specs is None else specs):
        targets=spec.get(platform+"_cache",[])
        if not targets:
            continue
        # A stale p4a completion marker must never bless a partial archive.
        if platform=="android":
            for relative in targets:
                target=destination/relative
                if not target.is_file() or sha256(target)!=spec["sha256"]:
                    target.with_name(".mark-"+target.name).unlink(missing_ok=True)
        source=ensure_archive(cache,spec)
        for relative in targets:
            target=destination/relative
            if not target.is_file() or sha256(target)!=spec["sha256"]:
                atomic_copy(source,target)
            if platform=="android":
                marker=target.with_name(".mark-"+target.name)
                marker.write_text("Verified SHA-256: "+spec["sha256"]+"\n")
        prepared.append(spec["id"])
    return prepared


def install_ios_archive_transport(recipe_class,cache,specs=None):
    """Cover build/pip/create and Kivy's temporary SDL-version probe alike."""
    cache=Path(cache).resolve()
    specs=source_specs() if specs is None else specs
    original=recipe_class.download_file
    def download(recipe,url,filename,cwd=None):
        if not url:
            return original(recipe,url,filename,cwd)
        spec=known_source(url,specs)
        if spec is None:
            return original(recipe,direct_archive_url(url),filename,cwd)
        source=ensure_archive(cache,spec)
        target=Path(cwd or ".")/filename
        if target.resolve()!=source.resolve():
            atomic_copy(source,target)
        return str(target)
    recipe_class.download_file=download
    return lambda:setattr(recipe_class,"download_file",original)
