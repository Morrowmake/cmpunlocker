# GPL modification notice: modified in the Morrowmake fork on 2026-10-02.
# Changes: P2P patch application and driver compatibility checks.
# Upstream/maintainer credits and original copyright/licence notices remain.
# See root LICENSE for this project's GPL-2.0-only terms.
import os
import pathlib
import shutil
import subprocess
import tempfile
import urllib.request

import pytest

import repo

URL = "https://github.com/NVIDIA/open-gpu-kernel-modules/archive/refs/tags/%s.tar.gz"
CACHE = pathlib.Path(os.environ.get("CMPUNLOCKER_BUILD_DIR", repo.ROOT / "driver" / ".build"))
PATCHES = repo.ROOT / "driver" / "patches"
ORDER = repo.patch_order()
VERSIONS = repo.versions()
assert VERSIONS, "driver/VERSION lists no versions"


def tarball(version):
    path = CACHE / ("open-gpu-kernel-modules-%s.tar.gz" % version)
    if not path.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(path.name + ".partial")
        with urllib.request.urlopen(URL % version, timeout=60) as resp, open(partial, "wb") as out:
            shutil.copyfileobj(resp, out)
        partial.replace(path)
    return path


def test_patch_order_covers_patch_dir():
    assert sorted(ORDER) == sorted(p.name for p in PATCHES.glob("*.patch"))


@pytest.mark.parametrize("version", VERSIONS)
def test_patches_apply(version):
    assert shutil.which("patch"), "GNU patch is not installed"
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["tar", "-xzf", str(tarball(version)), "-C", tmp], check=True)
        src = pathlib.Path(tmp, "open-gpu-kernel-modules-" + version)
        assert src.is_dir(), os.listdir(tmp)
        for name in ORDER:
            flags = ["-F0"] if name == "p2p-unlock.patch" else []
            r = subprocess.run(["patch", *flags, "-p1", "-i", str(PATCHES / name)], cwd=src,
                               stdin=subprocess.DEVNULL, capture_output=True, text=True)
            assert r.returncode == 0, "%s on %s:\n%s%s" % (name, version, r.stdout, r.stderr)

        gpu = (src / "src/nvidia/src/kernel/gpu/gpu.c").read_text()
        assert 'NvU32 trapPlm = GPU_REG_RD32(pGpu, 0x0012277cU);' in gpu
        assert 'if (trapPlm == 0xFFFFFFFFU)' in gpu
        if version.startswith("615."):
            assert 'pGpu->bPcieP2PSkipChipsetCheck = p2pCapsParams.bSkipChipsetCheck;' in gpu
