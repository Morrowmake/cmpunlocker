#!/usr/bin/env python3
"""Compare every destination byte after CUDA peer copies on all ordered pairs."""
import ctypes as ct
import os
import sys

SIZES = (128 * 1024 - 1, 128 * 1024, 128 * 1024 + 1,
         512 * 1024 - 1, 512 * 1024, 512 * 1024 + 1,
         1024 * 1024, 8 * 1024 * 1024, 32 * 1024 * 1024)


class CUDA:
    def __init__(self):
        self.lib = ct.CDLL("libcuda.so.1")
        ptr, devptr, size = ct.c_void_p, ct.c_uint64, ct.c_size_t
        signatures = {
            "cuInit": [ct.c_uint],
            "cuDeviceGetCount": [ct.POINTER(ct.c_int)],
            "cuDeviceGet": [ct.POINTER(ct.c_int), ct.c_int],
            "cuDeviceCanAccessPeer": [ct.POINTER(ct.c_int), ct.c_int, ct.c_int],
            "cuCtxCreate_v2": [ct.POINTER(ptr), ct.c_uint, ct.c_int],
            "cuCtxDestroy_v2": [ptr],
            "cuCtxSetCurrent": [ptr],
            "cuCtxEnablePeerAccess": [ptr, ct.c_uint],
            "cuCtxSynchronize": [],
            "cuMemAlloc_v2": [ct.POINTER(devptr), size],
            "cuMemcpyHtoD_v2": [devptr, ptr, size],
            "cuMemcpyDtoH_v2": [ptr, devptr, size],
            "cuMemcpyPeer": [devptr, ptr, devptr, ptr, size],
        }
        for name, args in signatures.items():
            fn = getattr(self.lib, name)
            fn.argtypes, fn.restype = args, ct.c_int
        self.call("cuInit", 0)

    def call(self, name, *args):
        status = getattr(self.lib, name)(*args)
        if status:
            raise RuntimeError(f"{name}: CUDA error {status}")

    def devices(self):
        count = ct.c_int()
        self.call("cuDeviceGetCount", ct.byref(count))
        result = []
        for ordinal in range(count.value):
            device = ct.c_int()
            self.call("cuDeviceGet", ct.byref(device), ordinal)
            result.append(device.value)
        return result

    def create(self, device):
        context = ct.c_void_p()
        self.call("cuCtxCreate_v2", ct.byref(context), 0, device)
        return context

    def current(self, context):
        self.call("cuCtxSetCurrent", context)

    def enable(self, device, peer, peer_context):
        supported = ct.c_int()
        self.call("cuDeviceCanAccessPeer", ct.byref(supported), device, peer)
        if not supported.value:
            raise RuntimeError(f"peer access unsupported: {device}->{peer}")
        self.call("cuCtxEnablePeerAccess", peer_context, 0)

    def allocate(self, size):
        pointer = ct.c_uint64()
        self.call("cuMemAlloc_v2", ct.byref(pointer), size)
        return pointer

    def upload(self, pointer, data):
        host = ct.create_string_buffer(data, len(data))
        self.call("cuMemcpyHtoD_v2", pointer, host, len(data))

    def download(self, pointer, size):
        host = ct.create_string_buffer(size)
        self.call("cuMemcpyDtoH_v2", host, pointer, size)
        return host.raw

    def copy(self, dest, dest_context, source, source_context, size):
        self.call("cuMemcpyPeer", dest, dest_context, source, source_context, size)
        self.call("cuCtxSynchronize")

    def destroy(self, context):
        # Destroying the private context also frees its allocations and peer maps.
        self.call("cuCtxDestroy_v2", context)


def check(cuda, sizes=SIZES):
    devices = cuda.devices()
    if len(devices) < 2:
        raise RuntimeError("at least two visible CUDA devices are required")
    contexts, pointers = [], []
    try:
        for device in devices:
            context = cuda.create(device)
            contexts.append(context)
            cuda.current(context)
            pointers.append(cuda.allocate(max(sizes)))
        for source in range(len(devices)):
            for dest in range(len(devices)):
                if source == dest:
                    continue
                cuda.current(contexts[source])
                cuda.enable(devices[source], devices[dest], contexts[dest])
        cases = 0
        for source in range(len(devices)):
            for dest in range(len(devices)):
                if source == dest:
                    continue
                for size in sizes:
                    expected = os.urandom(size)
                    cuda.current(contexts[source])
                    cuda.upload(pointers[source], expected)
                    cuda.current(contexts[dest])
                    # Every byte starts wrong, including the boundary bytes.
                    cuda.upload(pointers[dest], expected.translate(
                        bytes.maketrans(bytes(range(256)), bytes(reversed(range(256))))))
                    cuda.copy(pointers[dest], contexts[dest], pointers[source],
                              contexts[source], size)
                    actual = cuda.download(pointers[dest], size)
                    if actual != expected:
                        bad = sum(a != b for a, b in zip(actual, expected))
                        raise RuntimeError(f"{source}->{dest} {size} bytes: {bad} bad bytes")
                    print(f"PASS {source}->{dest} {size} bytes", flush=True)
                    cases += 1
        print(f"PASS: {cases} content checks, {len(devices)} devices", flush=True)
        return cases
    finally:
        for context in reversed(contexts):
            cuda.destroy(context)


def main():
    try:
        check(CUDA())
    except (OSError, AttributeError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
