"""Benchmark sintético de descarga Yahoo: código anterior vs nuevo (mismas latencias simuladas)."""
import time, sys, importlib
from unittest import mock
RTT=0.12; LOGIN=1.0; DB=0.04
class Imap:
    def __init__(self,*a,**k): time.sleep(LOGIN)
    def select(self,*a,**k): time.sleep(RTT); return "OK",[b"1"]
    def uid(self,cmd,ids,spec):
        time.sleep(RTT)
        out=[]
        for u in str(ids).split(","):
            raw=f"Subject: s{u}\r\nFrom: a@b.c\r\nDate: Thu, 1 Oct 2026 10:00:00 +0000\r\n\r\nbody".encode()
            out.append((f"1 (UID {u} FLAGS (\\Seen) BODY[] {{{len(raw)}}}".encode(),raw)); out.append(b")")
        return "OK",out
    def logout(self): pass
class Q:
    n=1
    def insert(self,rows,*a,**k):
        self.n=len(rows) if isinstance(rows,list) else 1; return self
    def __getattr__(self,n): return lambda *a,**k:self
    def execute(self):
        time.sleep(DB); return type("R",(),{"data":[{"id":f"x{i}"} for i in range(self.n)]})()
class St:
    client=type("C",(),{"table":lambda self,n:Q()})()
def run(modname,n,batch):
    m=importlib.import_module(f"app.services.{modname}")
    refs=[m.encode_yahoo_ref("Inbox",str(1000+i)) if hasattr(m,"encode_yahoo_ref") else f"Inbox\x1f{1000+i}" for i in range(n)]
    with mock.patch.object(m,"OAuthStorage",St), mock.patch.object(m,"_open_mailbox_client",lambda *a,**k:Imap()), \
         mock.patch.object(m,"_existing_message_ids",lambda **k:set()), mock.patch.object(m,"_select_folder",lambda *a,**k:None), \
         mock.patch.object(m,"_get_or_create_thread",lambda **k:(time.sleep(2*DB),{"id":"t"})[1]), \
         mock.patch.object(m,"_prepare_imap_secret",lambda e,p,**k:(e,p)):
        t0=time.monotonic(); off=0
        while off<n:
            r=m.sync_yahoo_page(account={"id":"a","email":"x@yahoo.com"},app_password="p",refs=refs,offset=off,batch_size=batch)
            off+=r["page_found"]
        return n*60/(time.monotonic()-t0)
n=200
old=run("_yahoo_import_old",n,25); new=run("yahoo_import",n,50)
print(f"descarga sintética {n} msgs: antes {old:.0f}/min, después {new:.0f}/min, x{new/old:.1f}")
