import importlib.util
import subprocess

import pytest

import repo

BASE = 'options nvidia NVreg_RegistryDwords="RmForceEnableGen2=1;RMPcieLinkSpeed=0x1'
PLAIN = BASE + '"\n'
P2P = BASE + ';ForceP2P=0x11"\n'


def configure(path, flag):
    subprocess.run(['bash', '-c',
                    'source "$1"; write_pcie_config "$2" "$3"', 'test',
                    str(repo.ROOT / 'common/pcie-config.sh'), str(path), str(flag)],
                   check=True)
    return path.read_text()


@pytest.mark.parametrize('initial,flag,expected', [
    (None, 0, PLAIN), (None, 1, P2P), (PLAIN, 1, P2P),
    (P2P, 1, P2P), (P2P, 0, P2P), (PLAIN, 0, PLAIN),
    (P2P.replace('0x11', '17'), 0, P2P),
    (P2P.replace('0x11', '0'), 0, PLAIN),
    ('# ' + P2P, 0, PLAIN), ('  ' + P2P, 0, P2P),
])
def test_pcie_configuration(tmp_path, initial, flag, expected):
    config = tmp_path / 'pcie.conf'
    if initial is not None:
        config.write_text(initial)
    assert configure(config, flag) == expected
    assert configure(config, flag) == expected


def test_installer_writes_combined_config():
    text = (repo.ROOT / 'install.sh').read_text()
    assert '--p2p) CONFIGURE_P2P=1 ;;' in text
    assert 'source "${SCRIPT_DIR}/common/pcie-config.sh"' in text
    assert 'write_pcie_config /etc/modprobe.d/cmp-pcie-gen2.conf "${CONFIGURE_P2P}"' in text
    assert text.index('write_pcie_config /etc/modprobe.d') < text.index('"${SCRIPT_DIR}/driver/build.sh"')


spec = importlib.util.spec_from_file_location(
    'p2p_check', repo.ROOT / 'tools/p2p-content-check.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class MemoryCUDA:
    def __init__(self, devices=4, corrupt=False, supported=True):
        self.count, self.corrupt, self.supported = devices, corrupt, supported
        self.memory, self.enabled, self.copies, self.destroyed = {}, [], [], []

    def devices(self):
        return list(range(self.count))

    def create(self, device):
        return device

    def current(self, context):
        self.context = context

    def enable(self, device, peer, peer_context):
        if not self.supported:
            raise RuntimeError('unsupported')
        self.enabled.append((device, peer))

    def allocate(self, size):
        self.memory[self.context] = bytes(size)
        return self.context

    def upload(self, pointer, data):
        assert self.context == pointer
        self.memory[pointer] = data

    def download(self, pointer, size):
        assert self.context == pointer
        return self.memory[pointer][:size]

    def copy(self, dest, dest_context, source, source_context, size):
        assert self.context == dest_context == dest
        assert source_context == source
        assert (source, dest) in self.enabled and (dest, source) in self.enabled
        assert all(a != b for a, b in zip(self.memory[dest], self.memory[source]))
        self.memory[dest] = self.memory[source][:size]
        if self.corrupt:
            self.memory[dest] = self.memory[dest][:-1] + bytes([self.memory[dest][-1] ^ 1])
        self.copies.append((source, dest, size))

    def destroy(self, context):
        self.destroyed.append(context)


def test_content_check_all_pairs_and_sizes(capsys):
    cuda = MemoryCUDA()
    assert checker.check(cuda) == 108
    assert set(cuda.copies) == {(a, b, n) for a in range(4) for b in range(4)
                               if a != b for n in checker.SIZES}
    assert len(cuda.enabled) == 12
    assert cuda.destroyed == [3, 2, 1, 0]


@pytest.mark.parametrize('size', checker.SIZES)
def test_content_check_detects_last_byte_corruption(size):
    cuda = MemoryCUDA(devices=2, corrupt=True)
    with pytest.raises(RuntimeError, match='1 bad bytes'):
        checker.check(cuda, sizes=(size,))
    assert cuda.destroyed == [1, 0]


def test_content_check_rejects_unsupported():
    cuda = MemoryCUDA(devices=2, supported=False)
    with pytest.raises(RuntimeError, match='unsupported'):
        checker.check(cuda, sizes=(8,))
    assert not cuda.copies
    assert cuda.destroyed == [1, 0]


def test_content_check_rejects_single_device():
    with pytest.raises(RuntimeError, match='at least two'):
        checker.check(MemoryCUDA(devices=1))


def test_main_reports_missing_driver(monkeypatch, capsys):
    def unavailable():
        raise OSError('CUDA driver unavailable')
    monkeypatch.setattr(checker, 'CUDA', unavailable)
    assert checker.main() == 1
    assert 'FAIL: CUDA driver unavailable' in capsys.readouterr().err
