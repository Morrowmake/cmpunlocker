## Morrowmake PCIe P2P fork

This fork tracks [upstream master](https://github.com/amoghmunikote/cmpunlocker)
(base `6c442ee`). It adds working PCIe peer-to-peer copies on CMP 170HX using
the maintainer's `P2P` branch and opens `TRAP31_PLM` through the Booter when
`ForceP2P` enables peer reads or writes, allowing the mailbox trap to arm.

The patch set applies to 610.43.02, 610.43.03, 610.57.04 and 615.71.09;
the four-card hardware result below was measured with 610.57.04.

With the requirements below installed, run:

```bash
sudo ./install.sh --p2p --profile=8gb --no-iommu --no-passthrough
```

Use `--profile=10gb` for 10GB cards; omit `--no-iommu` or `--no-passthrough`
if you want the corresponding setup. The installer writes this combined line
and retains P2P on subsequent installs:

```text
options nvidia NVreg_RegistryDwords="RmForceEnableGen2=1;RMPcieLinkSpeed=0x1;ForceP2P=0x11"
```

Stop GPU workloads before a module reload. The installer attempts a live reload;
if the modules remain busy, stop their users and reload the NVIDIA modules, or
cold boot. If memory stays at its stock size, power off completely before booting.

Verify actual data movement after loading the patched modules:

```bash
python3 tools/p2p-content-check.py
```

The standalone checker needs Python 3 and the NVIDIA CUDA driver, without PyTorch
or a CUDA toolkit. It enables peer access on every ordered pair, copies fresh
random bytes at 128 KiB−1/128 KiB/128 KiB+1, 512 KiB−1/512 KiB/512 KiB+1,
and 1, 8, 32 MiB, then reads the destination in its owning context and compares
every byte. Any unsupported pair, CUDA error, or mismatch exits nonzero.
`nvidia-smi topo` and reported peer support alone do not verify contents.
The check covers peer copies; applications using IPC or collectives should also
validate their own transfers.

On a four-card CMP 170HX system, the full peer-content checks passed on all 12
ordered pairs. Measured 16 MiB copies on pairs 0↔1 and 0↔2 reached approximately
**6.65 GB/s each way**, with contents verified (610.57.04, PCIe Gen2 x16).
See [credits](CREDITS.md) for the P2P code and original trap approach.

---

<div align="center" style="text-align: center;">
  <img width="1280" height="300" alt="cmpunlocker banner" src="https://github.com/user-attachments/assets/6edceb8e-afcb-43a4-b5b2-4321d81284d1" />
</div>

---

## What is cmpunlocker?

<p>
  cmpunlocker restores numerous features that are restricted in firmware/OTP configuration of the NVIDIA CMP 170HX. cmpunlocker has been featured by multiple outlets like wccftech, Tom's Hardware and LinusTechTips.
</p>

<table>
  <tr>
    <td><a href="https://www.youtube.com/watch?v=pvSdeU13hKc" title=""><img src="https://github.com/user-attachments/assets/be0a9cab-19b6-47c4-91cd-cb6a98be406f"></a></td>
    <td><a href="https://www.tomshardware.com/pc-components/gpus/nvidia-crypto-mining-gpus-hacked-to-restore-locked-away-vram-in-order-to-feed-ai-boom-software-mod-unlocks-64gb-of-vram-on-usd250-cmp-170hx" title="Article by Tom's Hardware"><img src="https://github.com/user-attachments/assets/e801b2b3-3002-4346-a9ad-6b228ef62b6a"></a></td>
    <td><a href="https://wccftech.com/nvidia-cmp-170hx-8-10-gb-prices-explode-over-1000-usd-as-tool-unlocks-hidden-64-80gb-vram/" title="Article by wccftech"><img src="https://github.com/user-attachments/assets/475b5acf-999b-430c-8ede-1c39e9fd6b97"></a></td>
  </tr>
</table>

**[Join our Discord community](https://discord.gg/CdHSakKSFv)** for support and discussions.

---

## Proof of Concept

Below are memory and performance results after applying the unlock:

<table>
  <tr>
    <td><b>Memory Unlock Results</b></td>
  </tr>
  <tr>
    <td><img alt="memory unlock" src="https://github.com/user-attachments/assets/ae062bd8-e3a7-4e73-b9a4-fbcde53f3c7b" width="100%" style="max-width: 900px;" /></td>
  </tr>
</table>

<table>
  <tr>
    <td><b>Performance Benchmarks (<a href="https://github.com/ProjectPhysX/OpenCL-Benchmark">OpenCL-Benchmark</a>)</b></td>
  </tr>
  <tr>
    <td><img alt="performance benchmarks" src="https://github.com/user-attachments/assets/2501506d-420f-4014-9574-b1bd0290eb60" width="100%" style="max-width: 900px;" /></td>
  </tr>
</table>

---

## Requirements

- Linux (x86-64)
- Root access
- NVIDIA CMP 170HX
- **nvidia-open 610.xx.xx+ already installed** (libs + firmware)
- Kernel headers matching the running kernel (`linux-headers-$(uname -r)` / `kernel-devel`)
- Secure Boot disabled (patched modules are unsigned)
- Network access on first install (downloads matching stock `open-gpu-kernel-modules` sources)
- Python 3 (used at build time to select 8GB/10GB geometry)

---

## Install

To install cmpunlocker, run the following command:

```bash
sudo ./install.sh
```

To force a certain memory profile, use the `--profile` option:

```bash
sudo ./install.sh --profile=8gb    # 8GB card → 64GB unlock
sudo ./install.sh --profile=10gb   # 10GB card → 40GB unlock
```

Then perform a reboot.

## What Gets Unlocked

<table>
  <tr>
    <th>Feature</th>
    <th>Status</th>
  </tr>
  <tr>
    <td>Full SM compute throughput (SS0/SS1)</td>
    <td>Working ✓</td>
  </tr>
  <tr>
    <td>Memory geometry (64GB on 8GB cards, 40GB on 10GB cards)</td>
    <td>Working ✓</td>
  </tr>
  <tr>
    <td>PCIe Gen 2 speeds</td>
    <td>Working ✓</td>
  </tr>
  <tr>
    <td>Full BAR1 Size (64GB)</td>
    <td>Working ✓</td>
  </tr>
  <tr>
    <td>JTAG (Host2Jtag register access)</td>
    <td>Working ✓</td>
  </tr>
  <tr>
    <td>VFIO-based passthrough</td>
    <td>Working ✓</td>
  </tr>
  <tr>
    <td>GPU profiling</td>
    <td>Working ✓</td>
  </tr>
  <tr>
    <td>Persistence across reboot (patched modules)</td>
    <td>Working ✓</td>
  </tr>
</table>

---

## Uninstall

To uninstall cmpunlocker, run the following command:

```bash
sudo ./remove.sh --yes
```

Then perform a reboot.

## Contributions

Please read [docs/CONTRIBUTING.md](https://github.com/amoghmunikote/cmpunlocker/blob/master/docs/CONTRIBUTING.md) before opening a PR.

## Support & Community

Having issues? Need help? Join our [Discord community](https://discord.gg/CdHSakKSFv) to discuss with other users and get support.
