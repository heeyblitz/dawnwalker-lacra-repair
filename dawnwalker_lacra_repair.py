#!/usr/bin/env python3
"""
The Blood of Dawnwalker - BETA Lacra / A Friend Like This repair

BETA / EXPERIMENTAL
===================

This is a continuation of the public q103 save research/fix by AiKiKun
(and Claude Opus 5). The original q103 fix restores the q103 quest graph
and removes q103 facts. In one tested save, that was not enough: the q103
encounter started but Lacra was invisible.

This beta script adds the additional Lacra actor-state patch that was
successfully tested on one Steam save pair:

    GOOD.sav    = an earlier save where Lacra's state is known-good
    CURRENT.sav = the save whose progress must be preserved

It can:
  1. Restore q103 (optional; enabled by default).
  2. Patch a specific Lacra/RebelAISubsystem serialized record by taking
     the 25-byte Lacra state observed in the GOOD save and transplanting it
     into CURRENT.
  3. Write a NEW save. Original saves are never modified.

IMPORTANT:
  - This is BETA. It was validated on the author's tested save pair, not
    across arbitrary Dawnwalker saves.
  - Always keep backups.
  - Disable/pause Steam Cloud while testing, or make sure it cannot replace
    the file you are testing.
  - If the Lacra signature cannot be found uniquely in both saves, the
    script aborts rather than guessing.
  - The Lacra patch is deliberately small: 25 bytes inside RebelAISubsystem.
    It does NOT copy the whole RebelAISubsystem from the old save.

Tested format:
  SaveVersion 134 / game 1.0.5-era DSAV saves.

Usage:
  python dawnwalker_lacra_repair_beta.py \
      --good ManualSave75.sav \
      --current ManualSave79.sav \
      --output ManualSave_LacraFix.sav \
      --oodle-dll oo2core_9_win64.dll

Analyze without writing:
  python dawnwalker_lacra_repair_beta.py --good GOOD.sav --current CURRENT.sav \
      --analyze --oodle-dll oo2core_9_win64.dll

Only the experimental Lacra patch (do not reset q103):
  ... --no-q103

Credits:
  Original q103 save research/fix: AiKiKun + Claude Opus 5
  This beta Lacra-state continuation was derived from a separate save
  comparison and tested on one affected playthrough.
"""

import argparse
import ctypes
import datetime
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------------------
# Oodle / Kraken decompression

class Decompressor:
    def __init__(self, dll=None, ooz=None):
        self.dll = self.ooz = None
        if dll:
            self.dll = ctypes.WinDLL(dll) if os.name == 'nt' else ctypes.CDLL(dll)
            f = self.dll.OodleLZ_Decompress
            f.restype = ctypes.c_int64
            f.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64,
                          ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_int64,
                          ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_int]
        elif ooz:
            self.ooz = ooz
        else:
            raise SystemExit('Need --oodle-dll or --ooz for decompression')

    def __call__(self, src, usize):
        if self.dll:
            dst = ctypes.create_string_buffer(usize)
            r = self.dll.OodleLZ_Decompress(src, len(src), dst, usize, 1, 0, 0, None, 0,
                                            None, None, None, 0, 3)
            if r != usize:
                raise SystemExit('Oodle decompression failed (%d)' % r)
            return dst.raw
        with tempfile.TemporaryDirectory() as t:
            a, b = os.path.join(t, 'c'), os.path.join(t, 'u')
            open(a, 'wb').write(struct.pack('<Q', usize) + src)
            subprocess.run([self.ooz, '-d', a, b], check=True, capture_output=True)
            out = open(b, 'rb').read()
            if len(out) < usize:
                raise SystemExit('ooz decompression failed')
            return out[:usize]

# ---------------------------------------------------------------------------
# DSAV container

def dsav_read(path, dec):
    d = open(path, 'rb').read()
    if d[:4] != b'DSAV':
        raise SystemExit('%s is not a Dawnwalker save (no DSAV header)' % path)
    hdr = d[:36]
    p = 36
    raw = b''
    while d[p:p + 4] == b'CHNK':
        csz, usz = struct.unpack_from('<II', d, p + 4)
        blk = d[p + 12:p + 12 + csz]
        raw += blk[2:2 + usz] if blk[0] & 0x40 else dec(blk, usz)
        p += 12 + csz
    return hdr, raw


def dsav_write(hdr, raw, path):
    CH = 0x20000
    body = b''
    table = []
    for i in range(0, len(raw), CH):
        blk = raw[i:i + CH]
        c = b'\xcc\x06' + blk  # Kraken stored/uncompressed block accepted by the game
        body += b'CHNK' + struct.pack('<II', len(c), len(blk)) + c
        table.append((len(c), len(blk)))
    h = bytearray(hdr)
    struct.pack_into('<I', h, 28, len(body))
    tail = (b'VASD' + struct.pack('<I', len(table)) +
            b''.join(struct.pack('<II', *t) for t in table) + b'VASD')
    open(path, 'wb').write(bytes(h) + body + tail)

# ---------------------------------------------------------------------------
# Dawnwalker node tree

def names(d):
    i = d.rfind(b'NAMEDWNT')
    j = d.rfind(b'NAME', 0, i)
    p = j + 8
    out = []
    while p < i:
        L = d[p]
        out.append(d[p + 1:p + 1 + L].decode('latin1'))
        p += 1 + L
    return out


def tree(d):
    nm = names(d)
    N = struct.unpack_from('<H', d, d.rfind(b'NAMEDWNT') + 8)[0]
    start = len(d) - 16 - 16 * N
    return nm, [struct.unpack_from('<HhIII', d, start + 16 * k) for k in range(N)]


def node(d, name):
    nm, recs = tree(d)
    for i, r in enumerate(recs):
        if i and nm[r[4]] == name:
            return i, d[r[2] - 36:r[2] - 36 + r[3]]
    raise SystemExit('Node %s not found' % name)


def replace_nodes(hdr, d, repl):
    """Replace node payloads. repl = {node_index: new_bytes}."""
    d = bytearray(d)
    hdr = bytearray(hdr)
    nm, recs = tree(bytes(d))
    N = len(recs)
    items = []
    for i, nb in repl.items():
        nabs = recs[i][2] - 36
        nsz = recs[i][3]
        items.append((nabs, nsz, i, nb))
    for nabs, nsz, ri, nb in sorted(items, reverse=True):
        delta = len(nb) - nsz
        d = d[:nabs] + nb + d[nabs + nsz:]
        ins = nabs + nsz
        end = len(d) - 16
        start = end - 16 * N
        for k in range(1, N):
            p = start + 16 * k
            a, par, off, sz, n = struct.unpack_from('<HhIII', d, p)
            o = off - 36
            if k == ri:
                sz += delta
            elif o >= ins and delta:
                off += delta
            elif o < nabs and o + sz >= ins:
                sz += delta
            struct.pack_into('<HhIII', d, p, a, par, off, sz, n)
        m, off, sz = struct.unpack_from('<iII', d, end)
        if off - 36 >= ins:
            struct.pack_into('<iII', d, end, m, off + delta, sz)
        for fo in (16, 20, 24):
            v = struct.unpack_from('<I', hdr, fo)[0]
            if v - 36 >= ins:
                struct.pack_into('<I', hdr, fo, v + delta)
    return bytes(hdr), bytes(d)

# ---------------------------------------------------------------------------
# q103 logic (from the original public fix)

T = []
for i in range(256):
    c = i << 24
    for _ in range(8):
        c = ((c << 1) ^ 0x04C11DB7) & 0xffffffff if c & 0x80000000 else (c << 1) & 0xffffffff
    T.append(c)


def fact_hash(s):
    h = 0
    for ch in s.upper():
        o = ord(ch)
        h = ((h >> 8) & 0xFFFFFF) ^ T[(h ^ o) & 0xFF]
        h = ((h >> 8) & 0xFFFFFF) ^ T[(h ^ (o >> 8)) & 0xFF]
    return h


Q103_FACTS = '''Fact.uriash_village_location_known q.m.103.fact.BadCop q.m.103.fact.CoensUltimatum q.m.103.fact.GoodCop
q.m.103.fact.HuntDrunk q.m.103.fact.InterrogationCount q.m.103.fact.LacraKnowsCoensHalfV q.m.103.fact.LacraKnowsWhoCoenIs
q.m.103.fact.NishIntel q.m.103.fact.NishToldAboutElder q.m.103.fact.ProtectedNishFromLacra q.m.103.fact.coen_joked
q.m.103.fact.got_info q.m.103.fact.interrogation_done q.m.103.fact.investigation_can_proceed
q.m.103.fact.investigation_door_opened q.m.103.fact.lacra_absorbed q.m.103.fact.lacra_asked_what_not
q.m.103.fact.lacra_cooperation q.m.103.fact.lacra_drink q.m.103.fact.lacra_duel_victory q.m.103.fact.lacra_found
q.m.103.fact.lacra_in_house q.m.103.fact.lacra_killed q.m.103.fact.lacra_left q.m.103.fact.lacra_met
q.m.103.fact.lacra_no_cooperation q.m.103.fact.lacra_refused q.m.103.fact.nish_died q.m.103.fact.nish_died.by_bloodhunger
q.m.103.fact.nish_fate_setup q.m.103.fact.nish_killed_after_info q.m.103.fact.nish_necrospeak q.m.103.fact.pre_lacra_hp
q.m.103.fact.proceed q.m.103.fact.proceed_check q.m.103.fact.int.nish_survived q.m.103.int.alley_found
q.m.103.int.alley_investigated q.m.103.int.checked_roof.01 q.m.103.int.checked_roof.02 q.m.103.int.checked_roof.03
q.m.103.int.checked_roof.04 q.m.103.int.checked_roof.05 q.m.103.int.checked_roof.06 q.m.103.int.checked_roof.07
q.m.103.int.nish_decision q.m.103.int.too_late'''.split()

PROGRESSED = [
    'q.m.103.fact.village_entered', 'q.m.103.fact.uriash_part_done',
    'q.m.103.fact.lacra_with_us', 'q.m.103.fact.path_proceed',
    'q.m.103.fact.peaceful_done'
]

ROOT = 0xc77b3abb6f87acd9
Q103_NODES = [(ROOT, 18878)] + \
    [(0x91fbd38d3a5818b7, n) for n in (4421, 3641, 15178, 23261, 29332, 14980)] + \
    [(0xa00b3ec90b1379fd, n) for n in (11110, 21931, 27316, 11140, 8703, 9531, 539, 17615, 11888, 15473, 21367)] + \
    [(0x17d5904522f26c65, n) for n in (17105, 23545)] + \
    [(0x7d05516b850846c1, n) for n in (22821, 27212, 6482, 22416, 29450, 5133)] + \
    [(0x17d5904522f26c65, 23122)]
NULL = (0, 2**64 - 1, 0)


def patch_helper(b):
    L = struct.unpack_from('<H', b, 4)[0]
    o = 6 + L
    n = struct.unpack_from('<I', b, o)[0]
    o += 4 + 8 * n
    cnt = struct.unpack_from('<H', b, o)[0]
    eo = o + 2
    E = [struct.unpack_from('<QQQ', b, eo + 24 * i) for i in range(cnt)]
    if any(e[0] == ROOT and e[1] == 18878 for e in E):
        return b, 0, True
    b = bytearray(b)
    present = {(e[0], e[1]) for e in E}
    todo = [(h, nn, 0) for h, nn in Q103_NODES if (h, nn) not in present]
    nulls = [i for i, e in enumerate(E) if e == NULL]
    extra = b''
    for k, e in enumerate(todo):
        if k < len(nulls):
            struct.pack_into('<QQQ', b, eo + 24 * nulls[k], *e)
        else:
            extra += struct.pack('<QQQ', *e)
            cnt += 1
    if extra:
        struct.pack_into('<H', b, o, cnt)
        end = eo + 24 * (cnt - len(extra) // 24)
        b = b[:end] + extra + b[end:]
    return bytes(b), len(todo), False


def patch_facts(b):
    n = struct.unpack_from('<I', b, 6)[0]
    ents = [struct.unpack_from('<Ii', b, 10 + 8 * i) for i in range(n)]
    have = {h for h, _ in ents}
    progressed = [x for x in PROGRESSED if fact_hash(x) in have]
    if progressed:
        return b, 0, progressed
    drop = {fact_hash(x) for x in Q103_FACTS}
    keep = [e for e in ents if e[0] not in drop]
    return b[:6] + struct.pack('<I', len(keep)) + b''.join(struct.pack('<Ii', *e) for e in keep), n - len(keep), []

# ---------------------------------------------------------------------------
# BETA Lacra patch
#
# This signature was found uniquely inside RebelAISubsystem in the tested
# GOOD/CURRENT pair. The 25-byte field at +19 is the state that was
# transplanted from GOOD into CURRENT in the successful test.

LACRA_ANCHOR = bytes.fromhex('20 43 6f 06 9b 3b 00')
LACRA_OFFSET = 19
LACRA_PATCH_LEN = 25


def lacra_signature(b):
    poss = []
    p = 0
    while True:
        p = b.find(LACRA_ANCHOR, p)
        if p < 0:
            break
        poss.append(p)
        p += 1
    return poss


def patch_lacra(good_b, current_b):
    gp = lacra_signature(good_b)
    cp = lacra_signature(current_b)
    if len(gp) != 1 or len(cp) != 1:
        raise SystemExit(
            'BETA Lacra signature was not unique: GOOD=%d CURRENT=%d. '
            'Refusing to guess. Try --analyze and report the saves.' % (len(gp), len(cp))
        )
    gs, cs = gp[0] + LACRA_OFFSET, cp[0] + LACRA_OFFSET
    if gs + LACRA_PATCH_LEN > len(good_b) or cs + LACRA_PATCH_LEN > len(current_b):
        raise SystemExit('Lacra beta patch region is outside RebelAISubsystem')
    src = good_b[gs:gs + LACRA_PATCH_LEN]
    before = current_b[cs:cs + LACRA_PATCH_LEN]
    if src == before:
        return current_b, gp[0], cp[0], before, src, False
    out = bytearray(current_b)
    out[cs:cs + LACRA_PATCH_LEN] = src
    return bytes(out), gp[0], cp[0], before, src, True

# ---------------------------------------------------------------------------


def save_meta_png(src, out):
    base = os.path.splitext(src)[0]
    outbase = os.path.splitext(out)[0]
    if os.path.exists(base + '.meta'):
        m = open(base + '.meta', 'rb').read()
        name = os.path.basename(outbase)
        m = re.sub(rb'"SaveName": "[^"]*"', b'"SaveName": "' + name.encode() + b'"', m)
        m = re.sub(rb'"Date": "[^"]*"', b'"Date": "' + datetime.datetime.now().strftime('%Y.%m.%d-%H.%M.%S').encode() + b'"', m)
        open(outbase + '.meta', 'wb').write(m)
    if os.path.exists(base + '.png'):
        shutil.copyfile(base + '.png', outbase + '.png')


def version(hdr):
    return struct.unpack_from('<H', hdr, 8)[0]


def analyze(good, current):
    gh, gd = good
    ch, cd = current
    gi, gb = node(gd, 'RebelAISubsystem')
    ci, cb = node(cd, 'RebelAISubsystem')
    gp = lacra_signature(gb)
    cp = lacra_signature(cb)
    print('BETA Lacra Repair analysis')
    print('===========================')
    print('GOOD SaveVersion :', version(gh))
    print('CURRENT SaveVersion:', version(ch))
    print('RebelAISubsystem sizes:', len(gb), '(good),', len(cb), '(current)')
    print('Lacra signature occurrences: GOOD=%d CURRENT=%d' % (len(gp), len(cp)))
    if len(gp) == 1 and len(cp) == 1:
        gs = gp[0] + LACRA_OFFSET
        cs = cp[0] + LACRA_OFFSET
        print('GOOD patch bytes   :', gb[gs:gs+LACRA_PATCH_LEN].hex(' '))
        print('CURRENT patch bytes:', cb[cs:cs+LACRA_PATCH_LEN].hex(' '))
        print('Would change Lacra field:', gb[gs:gs+LACRA_PATCH_LEN] != cb[cs:cs+LACRA_PATCH_LEN])
    try:
        _, qh = node(cd, 'QuestHelperImpl')
        _, qs = node(cd, 'QuestSystemImpl')
        qh2, restored, active = patch_helper(qh)
        qs2, dropped, progressed = patch_facts(qs)
        print('q103 active already :', active)
        print('q103 nodes to restore:', restored)
        print('q103 facts to remove :', dropped)
        if progressed:
            print('WARNING: current save appears past q103:', ', '.join(progressed))
    except Exception as e:
        print('q103 analysis error:', e)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--good', required=True, help='known-good reference save')
    ap.add_argument('--current', required=True, help='current save to preserve')
    ap.add_argument('--output', help='output .sav path')
    ap.add_argument('--oodle-dll', help='path to oo2core_9_win64.dll')
    ap.add_argument('--ooz', help='path to ooz executable')
    ap.add_argument('--analyze', action='store_true', help='analyze only; do not write')
    ap.add_argument('--no-q103', action='store_true', help='skip q103 repair; only apply beta Lacra patch')
    ap.add_argument('--no-lacra', action='store_true', help='skip beta Lacra patch; only apply q103 repair')
    args = ap.parse_args()

    dec = Decompressor(args.oodle_dll, args.ooz)
    good = dsav_read(os.path.abspath(args.good), dec)
    current = dsav_read(os.path.abspath(args.current), dec)

    if version(good[0]) != version(current[0]):
        raise SystemExit('GOOD and CURRENT have different SaveVersion values.')
    if version(current[0]) != 134:
        print('WARNING: tested on SaveVersion 134; current is', version(current[0]))

    if args.analyze:
        analyze(good, current)
        return

    hdr, d = current
    ghdr, gd = good
    replacements = {}
    report = []

    if not args.no_lacra:
        ri, rb = node(gd, 'RebelAISubsystem')
        ci, cb = node(d, 'RebelAISubsystem')
        patched, gp, cp, before, src, changed = patch_lacra(rb, cb)
        replacements[ci] = patched
        report.append('Lacra beta patch: %s (GOOD anchor=%d CURRENT anchor=%d)' %
                      ('changed' if changed else 'already identical', gp, cp))

    if not args.no_q103:
        ih, bh = node(d, 'QuestHelperImpl')
        iff, bf = node(d, 'QuestSystemImpl')
        nf, dropped, progressed = patch_facts(bf)
        if progressed:
            print('WARNING: current save contains facts indicating q103 is already past the initial stage:')
            for x in progressed:
                print('  ', x)
            print('Leaving QuestSystemImpl unchanged.')
        else:
            nh, restored, active = patch_helper(bh)
            replacements[ih] = nh
            replacements[iff] = nf
            report.append('q103: restored %d nodes, removed %d q103 facts%s' %
                          (restored, dropped, ' (already active)' if active else ''))

    if not replacements:
        raise SystemExit('Nothing selected to patch. Remove --no-q103/--no-lacra.')

    hdr2, d2 = replace_nodes(hdr, d, replacements)
    A, B, C = struct.unpack_from('<3I', hdr2, 16)
    assert d2[A - 36:A - 32] == b'NAME'
    assert d2[B - 36:B - 32] == b'DWNT'
    assert C - 36 == len(d2)

    out = args.output
    if not out:
        folder = os.path.dirname(os.path.abspath(args.current))
        out = os.path.join(folder, 'ManualSave_LacraFix_BETA.sav')
    out = os.path.abspath(out)
    if os.path.exists(out):
        raise SystemExit('Output already exists: %s' % out)

    dsav_write(hdr2, d2, out)
    save_meta_png(os.path.abspath(args.current), out)
    print('\n'.join(report))
    print('Written:', out)
    print('\nBETA WARNING: test with backups and Steam Cloud disabled/paused.')


if __name__ == '__main__':
    main()
