#!/usr/bin/env python3
"""VIAFLO packet framing and macOS Classic Bluetooth / serial transport.
Protocol derived from Willow Garage pipette_driver (BSD); see references and LICENSE.
"""
import datetime, json, queue, struct, subprocess, threading, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent

class ProtocolError(RuntimeError): pass

def frame(kind, body=b'', seq=1):
    p=bytearray(struct.pack('>HBHBH',len(body)+8,0,seq,0,kind)+body)
    p[2]=(-sum(p))&255
    return b'\x02'+b''.join(bytes((27,x)) if x in (2,3,27) else bytes((x,)) for x in p)+b'\x03\x03\x03\x0a'

class Decoder:
    def __init__(self): self.buf=None; self.escape=False
    def feed(self, chunk):
        results=[]
        for x in chunk:
            if self.buf is None:
                if x==2: self.buf=bytearray(); self.escape=False
                continue
            if self.escape:
                if x not in (2,3,27): raise ProtocolError('Invalid escape sequence')
                self.buf.append(x); self.escape=False
            elif x==27: self.escape=True
            elif x==2: self.buf=bytearray()
            elif x==3:
                results.append(bytes(self.buf)); self.buf=None
            else: self.buf.append(x)
            if self.buf is not None and len(self.buf)>8192: raise ProtocolError('Oversized frame')
        return results

def response(p, seq, kind, status_bytes=1):
    if len(p)<9 or int.from_bytes(p[:2],'big')!=len(p): raise ProtocolError('Response length mismatch')
    if sum(p)&255: raise ProtocolError('Response checksum mismatch')
    if int.from_bytes(p[3:5],'big')!=seq: raise ProtocolError('Response sequence mismatch')
    if int.from_bytes(p[6:8],'big')!=kind: raise ProtocolError('Response type mismatch')
    if len(p)<8+status_bytes: raise ProtocolError('Missing response status')
    status=int.from_bytes(p[8:8+status_bytes],'big')
    if status: raise ProtocolError(f'Pipette returned error {status}')
    return p

class Link:
    def __init__(self,address,channel=None,port=None,baud=None,remote=False):
        self.remote=remote
        ROOT.joinpath('logs').mkdir(exist_ok=True)
        self.log=ROOT/'logs'/f'{datetime.datetime.now():%Y%m%d-%H%M%S-%f}.jsonl'
        self.seq=0; self.decoder=Decoder(); self.q=queue.Queue(); self.proc=None; self.serial=None
        if port:
            import serial
            self.serial=serial.Serial(port,baudrate=baud,timeout=.1,write_timeout=3)
        else:
            cmd=[str(ROOT/'bluetooth'),'connect',address]+([str(channel)] if channel else [])
            self.proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
            def reader():
                for line in self.proc.stdout:
                    try:self.q.put(json.loads(line))
                    except ValueError:self.q.put({'event':'error','message':line})
                self.q.put({'event':'closed'})
            threading.Thread(target=reader,daemon=True).start()
            try:
                deadline=time.monotonic()+25
                while time.monotonic()<deadline:
                    e=self.event(deadline-time.monotonic())
                    if e['event']=='ready':break
                else:raise TimeoutError('Bluetooth connection timed out')
            except BaseException:self.close();raise
        print(f'Transcript: {self.log}')
    def record(self,**e):
        with self.log.open('a') as f:f.write(json.dumps(dict(time=datetime.datetime.now().isoformat(),**e))+'\n')
    def event(self,timeout):
        try:e=self.q.get(timeout=max(.001,timeout))
        except queue.Empty:raise TimeoutError('No Bluetooth response within timeout')
        self.record(**e)
        if e['event'] in ('error','closed') or (e['event']=='write' and e.get('status')):raise ConnectionError(str(e))
        return e
    def transact(self,kind,body=b'',timeout=5):
        self.seq=self.seq%65535+1; wire=frame(kind,body,self.seq)
        if self.remote:wire=wire[:-3]  # PC-control API uses a single ETX
        self.record(event='tx',hex=wire.hex(),kind=kind,seq=self.seq)
        if self.serial:self.serial.write(wire)
        else:self.proc.stdin.write(wire.hex()+'\n');self.proc.stdin.flush()
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if self.serial:
                chunk=self.serial.read(1024)
                if chunk:self.record(event='rx',hex=chunk.hex())
            else:
                e=self.event(deadline-time.monotonic());chunk=bytes.fromhex(e['hex']) if e['event']=='rx' else b''
            for p in self.decoder.feed(chunk):return response(p,self.seq,kind,2 if self.remote else 1)
        raise TimeoutError('No valid response; command outcome UNKNOWN. No automatic resend.')
    def close(self):
        if self.serial:self.serial.close()
        if self.proc:
            if self.proc.poll() is None:
                self.proc.stdin.close()
                try:self.proc.wait(timeout=2)
                except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait()
            self.proc.stdout.close()
