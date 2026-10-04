#!/bin/bash
# GPL modification notice: Morrowmake fork changes dated 2026-10-02.
# Changes: combined PCIe/P2P configuration and P2P retention on reinstall.
# Upstream/maintainer credits and original copyright/licence notices remain.
# See root LICENSE for this project's GPL-2.0-only terms.
# Keep the PCIe and P2P keys in one RegistryDwords value.
write_pcie_config() {
    local config_file="$1" enable_p2p="$2"
    local registry_dwords="RmForceEnableGen2=1;RMPcieLinkSpeed=0x1"
    if [[ -f "${config_file}" ]] &&
       grep -Eq '^[[:space:]]*options[[:space:]]+nvidia[[:space:]]+.*NVreg_RegistryDwords="([^"]*;)?ForceP2P=(0[xX]11|17)(;|")' "${config_file}"; then
        enable_p2p=1
    fi
    if (( enable_p2p == 1 )); then
        registry_dwords="${registry_dwords};ForceP2P=0x11"
    fi
    printf 'options nvidia NVreg_RegistryDwords="%s"\n' "${registry_dwords}" > "${config_file}"
}
