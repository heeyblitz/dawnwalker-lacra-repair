#!/usr/bin/env python3
"""
The Blood of Dawnwalker - continue Lacra's questline into "Song of the Mountain"
after "A Friend Like This" (q103) closed it (you protected Nish from Lacra,
refused to cooperate, etc.).

Why the questline closes: at the end of the interrogation q103 checks
q.m.103.fact.lacra_cooperation. Without it the investigation exits as
"LacraBanished" and the whole q103 quest ends, so Song of the Mountain
(which is part of the same quest) never starts.

Why simply restarting q103 does not work: q103 spawns the boss Lacra only once,
right at the quest start. A save edit that restores the quest in the middle
cannot re-run that step, so the duel in Lacra's house never starts (the cinematic
plays, then nobody is there). Earlier "restart" fixes run into exactly this.

What this script does instead (your original save is NEVER modified - a new
save slot is written):
  1. Marks A Friend Like This as finished WITH cooperation, by setting the
     outcome facts (Lacra met, duel won, info obtained, cooperation, ...) and
     removing the "no cooperation" ones (ProtectedNishFromLacra, ...).
  2. Puts q103 at the very beginning of the Song of the Mountain part
     (sub-quest q103_path), in its "Lacra is waiting for you" variant:
       - at NIGHT Lacra is placed at her meeting point,
       - talking to her plays the "Lacra by the mountain" scene and the quest
         continues normally from there.
     The "too late" timer (Lacra leaving after a few days) is not started.
  3. Writes the result as a new ManualSaveN (N = first free number) + .meta + .png.

After loading the new slot: wait until night and find Lacra. In the tested save
she was waiting in the cave next to Stonefall; guides place the meeting near
Crown Rock. There is no journal entry or map marker until you talk to her.

What you lose: the duel with Lacra and the Nish interrogation are skipped
(no XP for them). Nothing from them is needed later in Song of the Mountain.

Tested on: a Steam save with SaveVersion 134 (q103 closed with "no cooperation"),
patched and then played on game build CL-265636 (SaveVersion 136). Use at your own
risk, keep backups.

Decompression needs Oodle (Kraken). Provide ONE of:
  --oodle-dll path\\to\\oo2core_9_win64.dll   (Windows; ships with many UE games)
  --ooz path/to/ooz                         (https://github.com/powzix/ooz, CLI: ooz -d in out)
Writing does not need Oodle (the new save uses uncompressed Kraken blocks, the game accepts them).

Usage:
  python dawnwalker_lacra_fix_v2.py "C:\\Users\\<you>\\AppData\\Local\\Dawnwalker\\Saved\\SaveGames\\ManualSave1.sav" --ooz ooz.exe
"""
import argparse, ctypes, datetime, os, re, shutil, struct, subprocess, sys, tempfile

# ---------------------------------------------------------------- Oodle
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
            sys.exit('Need --oodle-dll or --ooz for decompression')

    def __call__(self, src, usize):
        if self.dll:
            dst = ctypes.create_string_buffer(usize)
            r = self.dll.OodleLZ_Decompress(src, len(src), dst, usize, 1, 0, 0, None, 0, None, None, None, 0, 3)
            if r != usize: sys.exit('Oodle decompression failed (%d)' % r)
            return dst.raw
        with tempfile.TemporaryDirectory() as t:
            a, b = os.path.join(t, 'c'), os.path.join(t, 'u')
            open(a, 'wb').write(struct.pack('<Q', usize) + src)   # ooz expects an 8-byte size header
            subprocess.run([self.ooz, '-d', a, b], check=True, capture_output=True)
            out = open(b, 'rb').read()
            if len(out) < usize: sys.exit('ooz decompression failed')
            return out[:usize]

# ---------------------------------------------------------------- DSAV container
def dsav_read(path, dec):
    d = open(path, 'rb').read()
    if d[:4] != b'DSAV': sys.exit('Not a Dawnwalker save (no DSAV header)')
    hdr = d[:36]; p = 36; raw = b''
    while d[p:p + 4] == b'CHNK':
        csz, usz = struct.unpack_from('<II', d, p + 4)
        blk = d[p + 12:p + 12 + csz]
        raw += blk[2:2 + usz] if blk[0] & 0x40 else dec(blk, usz)   # 0x40 = stored block
        p += 12 + csz
    return hdr, raw

def dsav_write(hdr, raw, path):
    CH = 0x20000; body = b''; table = []
    for i in range(0, len(raw), CH):
        blk = raw[i:i + CH]; c = b'\xcc\x06' + blk          # Kraken "uncompressed" block
        body += b'CHNK' + struct.pack('<II', len(c), len(blk)) + c; table.append((len(c), len(blk)))
    h = bytearray(hdr); struct.pack_into('<I', h, 28, len(body))
    tail = b'VASD' + struct.pack('<I', len(table)) + b''.join(struct.pack('<II', *t) for t in table) + b'VASD'
    open(path, 'wb').write(bytes(h) + body + tail)

# ---------------------------------------------------------------- node tree
def names(d):
    i = d.rfind(b'NAMEDWNT'); j = d.rfind(b'NAME', 0, i); p = j + 8; out = []
    while p < i:
        L = d[p]; out.append(d[p + 1:p + 1 + L].decode('latin1')); p += 1 + L
    return out

def tree(d):
    nm = names(d); N = struct.unpack_from('<H', d, d.rfind(b'NAMEDWNT') + 8)[0]
    start = len(d) - 16 - 16 * N
    return nm, [struct.unpack_from('<HhIII', d, start + 16 * k) for k in range(N)]

def node(d, name):
    nm, recs = tree(d)
    for i, r in enumerate(recs):
        if i and nm[r[4]] == name: return i, d[r[2] - 36:r[2] - 36 + r[3]]
    sys.exit('Node %s not found' % name)

def replace_nodes(hdr, d, repl):
    d = bytearray(d); hdr = bytearray(hdr)
    nm, recs = tree(bytes(d)); N = len(recs)
    for nabs, nsz, ri, nb in sorted(((recs[i][2] - 36, recs[i][3], i, nb) for i, nb in repl.items()), reverse=True):
        delta = len(nb) - nsz; d = d[:nabs] + nb + d[nabs + nsz:]; ins = nabs + nsz
        end = len(d) - 16; start = end - 16 * N
        for k in range(1, N):
            p = start + 16 * k; a, par, off, sz, n = struct.unpack_from('<HhIII', d, p); o = off - 36
            if k == ri: sz += delta
            elif o >= ins and delta: off += delta
            elif o < nabs and o + sz >= ins: sz += delta
            struct.pack_into('<HhIII', d, p, a, par, off, sz, n)
        m, off, sz = struct.unpack_from('<iII', d, end)
        if off - 36 >= ins: struct.pack_into('<iII', d, end, m, off + delta, sz)
        for fo in (16, 20, 24):
            v = struct.unpack_from('<I', hdr, fo)[0]
            if v - 36 >= ins: struct.pack_into('<I', hdr, fo, v + delta)
    return bytes(hdr), bytes(d)

# ---------------------------------------------------------------- fact name hash (UE Strihash_DEPRECATED, wide)
T = []
for i in range(256):
    c = i << 24
    for _ in range(8): c = ((c << 1) ^ 0x04C11DB7) & 0xffffffff if c & 0x80000000 else (c << 1) & 0xffffffff
    T.append(c)
def fact_hash(s):
    h = 0
    for ch in s.upper():
        o = ord(ch)
        h = ((h >> 8) & 0xFFFFFF) ^ T[(h ^ o) & 0xFF]; h = ((h >> 8) & 0xFFFFFF) ^ T[(h ^ (o >> 8)) & 0xFF]
    return h

# every q103 fact the interrogation / investigation can leave behind - cleared first
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
q.m.103.int.nish_decision q.m.103.int.too_late q.m.103.int.Lacra_wait'''.split()
# ... then set to the state "investigation finished, Lacra cooperates and waits for you"
SET_FACTS = [('q.m.103.int.Lacra_wait', 2), ('q.m.103.fact.lacra_cooperation', 1), ('q.m.103.fact.interrogation_done', 1),
             ('q.m.103.fact.proceed', 1), ('q.m.103.fact.lacra_found', 1), ('q.m.103.fact.lacra_met', 1),
             ('q.m.103.fact.lacra_duel_victory', 1), ('q.m.103.fact.got_info', 1), ('q.m.103.fact.pre_lacra_hp', 1),
             ('q.m.103.fact.investigation_can_proceed', 1), ('q.m.103.fact.investigation_door_opened', 1),
             ('q.m.103.int.alley_found', 1), ('q.m.103.int.alley_investigated', 5)] + \
            [('q.m.103.int.checked_roof.%02d' % i, 1) for i in range(1, 7)]
# if any of these is set, the player already got past A Friend Like This -> do not touch
PROGRESSED = ['q.m.103.fact.village_entered', 'q.m.103.fact.uriash_part_done', 'q.m.103.fact.lacra_with_us',
              'q.m.103.fact.path_proceed', 'q.m.103.fact.peaceful_done']

# QuestHelperImpl: a table of quest-graph instance paths (root index, sub-sketch node ids..., -1),
# then the active nodes as (instance id, node id, value). The instance id is XXH3-64 (seed 0)
# of the instance path packed as little-endian u64s, e.g. xxh3_64(pack('<3Q', 0, 18878, 16820)).
ROOT = 0xc77b3abb6f87acd9                        # (0,)                 Dawnwalker_main_s
MAIN = 0x91fbd38d3a5818b7                        # (0, 18878)           q103_main
PATH = 0x67168e74b9544923                        # (0, 18878, 16820)    q103_path (Song of the Mountain part)
PATH_RECORD = (0, 18878, 16820)
Q103_INSTANCES = {MAIN, PATH,
                  0xa00b3ec90b1379fd,            # (0, 18878, 15178)               rumours
                  0x17d5904522f26c65,            # (0, 18878, 29332)               q103_investigation
                  0x7d05516b850846c1,            # (0, 18878, 29332, 23545)        alley / house
                  0x4b2fc768e7e5317b,            # (0, 18878, 29332, 28945)        duel / interrogation
                  0xa838bcc66d70f539}            # (0, 18878, 29332, 28945, 26667) duel
ACTIVE = [(ROOT, 18878),                         # q103 running
          (MAIN, 4421), (MAIN, 14980),           # q103_main background waits
          (MAIN, 16820),                         # q103_path sub-quest running
          (MAIN, 18853),                         # village mask logic (started together with q103_path)
          (PATH, 31673), (PATH, 27106), (PATH, 6672), (PATH, 8142),
          (PATH, 16696),                         # talk to Lacra -> "Lacra by the mountain"
          (PATH, 9354),                          # night -> Lacra goes to her meeting point
          (PATH, 361)]
NULL = (0, 2**64 - 1, 0)

def patch_helper(b):
    L = struct.unpack_from('<H', b, 4)[0]; to = 6 + L
    n = struct.unpack_from('<I', b, to)[0]; tbl = list(struct.unpack_from('<%dQ' % n, b, to + 4)); o = to + 4 + 8 * n
    cnt = struct.unpack_from('<H', b, o)[0]; eo = o + 2
    E = [struct.unpack_from('<QQQ', b, eo + 24 * i) for i in range(cnt)]
    tail = b[eo + 24 * cnt:]
    if any(e[0] == ROOT and e[1] == 18878 for e in E):
        sys.exit('q103 is still ACTIVE in this save - this script is for saves where it already closed.')
    recs, cur = [], []
    for x in tbl:
        if x == 2**64 - 1: recs.append(tuple(cur)); cur = []
        else: cur.append(x)
    if PATH_RECORD not in recs: tbl += list(PATH_RECORD) + [2**64 - 1]     # never entered before
    E = [NULL if e[0] in Q103_INSTANCES else e for e in E]                 # drop leftovers, if any
    nulls = [i for i, e in enumerate(E) if e == NULL]
    for k, (h, nn) in enumerate(ACTIVE):
        if k < len(nulls): E[nulls[k]] = (h, nn, 0)
        else: E.append((h, nn, 0))
    if len(E) > 0xffff: sys.exit('too many active quest nodes')
    nb = b[:to] + struct.pack('<I', len(tbl)) + struct.pack('<%dQ' % len(tbl), *tbl) + \
        struct.pack('<H', len(E)) + b''.join(struct.pack('<QQQ', *e) for e in E) + tail
    return nb

def patch_facts(b):
    n = struct.unpack_from('<I', b, 6)[0]
    ents = [struct.unpack_from('<Ii', b, 10 + 8 * i) for i in range(n)]
    have = {h for h, _ in ents}
    if any(fact_hash(x) in have for x in PROGRESSED):
        sys.exit('This save is already past "A Friend Like This" (village reached) - aborting.')
    drop = {fact_hash(x) for x in Q103_FACTS}
    keep = [e for e in ents if e[0] not in drop] + [(fact_hash(k), v) for k, v in SET_FACTS]
    return b[:6] + struct.pack('<I', len(keep)) + b''.join(struct.pack('<Ii', *e) for e in keep)

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('save'); ap.add_argument('--oodle-dll'); ap.add_argument('--ooz')
    ap.add_argument('--out-name', help='output slot name, default: first free ManualSaveN')
    a = ap.parse_args()
    src = os.path.abspath(a.save); folder = os.path.dirname(src); base = src[:-4]
    hdr, d = dsav_read(src, Decompressor(a.oodle_dll, a.ooz))
    ver = struct.unpack_from('<H', hdr, 8)[0]
    if ver not in (134, 136): print('WARNING: SaveVersion %d, script was tested on 134 and 136' % ver)
    ih, bh = node(d, 'QuestHelperImpl'); iff, bf = node(d, 'QuestSystemImpl')
    nf = patch_facts(bf)
    nh = patch_helper(bh)
    hdr2, d2 = replace_nodes(hdr, d, {ih: nh, iff: nf})
    A, B, C = struct.unpack_from('<3I', hdr2, 16)
    assert d2[A - 36:A - 32] == b'NAME' and d2[B - 36:B - 32] == b'DWNT' and C - 36 == len(d2), 'internal check failed'
    name = a.out_name
    if not name:
        used = {int(m.group(1)) for f in os.listdir(folder) for m in [re.match(r'ManualSave(\d+)\.sav$', f)] if m}
        name = 'ManualSave%d' % (max(used | {0}) + 1)
    out = os.path.join(folder, name)
    if os.path.exists(out + '.sav'): sys.exit(out + '.sav already exists')
    dsav_write(hdr2, d2, out + '.sav')
    if os.path.exists(base + '.meta'):
        m = open(base + '.meta', 'rb').read()
        m = re.sub(rb'"SaveName": "[^"]*"', b'"SaveName": "' + name.encode() + b'"', m)
        m = re.sub(rb'"Date": "[^"]*"', b'"Date": "' + datetime.datetime.now().strftime('%Y.%m.%d-%H.%M.%S').encode() + b'"', m)
        open(out + '.meta', 'wb').write(m)
    if os.path.exists(base + '.png'): shutil.copyfile(base + '.png', out + '.png')
    print('Song of the Mountain set up (A Friend Like This finished with cooperation).')
    print('Written:', out + '.sav', '- load it, wait for night and find Lacra at her meeting point.')

if __name__ == '__main__':
    main()
