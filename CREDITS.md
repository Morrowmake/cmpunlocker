<!-- Modified by Morrowmake on 2026-10-04: pin source and adaptation credits. -->

# Credits

Thanks to: 
| Person | Feature |
|---|---|
| [asm64-hooligan](https://github.com/asm64-hooligan/) | Full BAR1 size (64GB) |
| [lesj0610](https://github.com/lesj0610/) | GPU profiling |

PCIe P2P: [amoghmunikote](https://github.com/amoghmunikote/cmpunlocker/tree/14b38f72dbe0ee03dfd9377880a0c83302f703d3)
for the [P2P mailbox trap code](https://github.com/amoghmunikote/cmpunlocker/blob/14b38f72dbe0ee03dfd9377880a0c83302f703d3/driver/patches/p2p-unlock.patch)
from the maintainer's `P2P` branch (GPL-2.0), and
[asm64-hooligan](https://github.com/asm64-hooligan/cmpunlocker/tree/a439e03442a14cd891b98d79fd60cc624a528c2e)
for the original trap approach.

Morrowmake's additions open the trap's privilege mask conditionally, preserve
the P2P settings on reinstall, adapt patch context for newer driver versions,
and provide a bytewise peer-copy check. These changes do not replace authorship
of the inherited code.

The patch repository retains its [GPL version 2 licence](LICENSE).
NVIDIA's original source notices and MIT/dual MIT-GPL module terms remain
applicable to the respective upstream files; see the downloaded source's
`COPYING`. The fork's GPL additions are not relicensed by those upstream terms.
