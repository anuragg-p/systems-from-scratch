"""A scripted language server, for kilo's module 07 tests and timeline. Standard library only.

kilo starts it as it starts clangd: KILO_LSP names a small shell script (track.py writes it)
that runs this file. It speaks the protocol on its standard input and output, and

    KILO_TEST_LSP_LOG        is a file it appends a JSON line to for each event: "start" (its
                             pid, parent, and the descriptors it has open), "recv" (each message
                             as it arrived: its header, its body, and the body as JSON), "send",
                             "eof", "exit"
    KILO_TEST_LSP_SCENARIO   is a Python file that changes what it does (optional): it may set
                             attributes of `srv` at the top level, and define
                                 on_start(srv)            run before anything is read
                                 on_message(srv, msg)     a message as JSON (None: not JSON);
                                                          return True if it was handled
                             srv.read = False makes it never read its input at all.

Unless a scenario says otherwise it is a tiny language server for a tiny language:
    - initialize: capabilities (positionEncoding: "utf-8" if offered first, like clangd; set
      srv.encoding to force one, None to leave it out), serverInfo {"scripted", "1.0"}
    - didOpen, didChange: publishDiagnostics for the text, with its version: every "oops" is an
      error, "use of undeclared identifier 'oops'"; every "meh" a warning, "unused variable 'meh'"
    - definition: the word at the position; its definition is the first "int WORD" in the text
    - shutdown: null; exit: exit(0); any other request: null
It also exits when its input ends, and on its own after srv.lifetime seconds or when kilo, its
parent, has gone, so a test can never leave it running.
"""

import json
import os
import re
import select
import signal
import sys
import threading
import time


class Server:
    def __init__(self):
        self.log_path = os.environ.get("KILO_TEST_LSP_LOG")
        self.read = True
        self.encoding = "auto"         # "auto": as clangd; or "utf-8", "utf-16", None
        self.server_info = {"name": "scripted", "version": "1.0"}
        self.capabilities = {"textDocumentSync": 1, "definitionProvider": True}
        self.lifetime = 120.0
        self.diagnose = True
        self.uri = None
        self.text = ""
        self.version = 0
        self.chosen = "utf-16"
        self.buf = b""
        self.parent = os.getppid()
        self.t0 = time.monotonic()

    # ------------------------------------------------------------ the log

    def log(self, event, **kw):
        if not self.log_path:
            return
        kw["event"] = event
        kw["t"] = round(time.monotonic() - self.t0, 4)
        kw["mono"] = time.monotonic()      # the system's monotonic clock, to set beside kilo's
        with open(self.log_path, "a") as f:
            f.write(json.dumps(kw) + "\n")

    # ------------------------------------------------------------ writing

    def frame(self, msg):
        body = msg if isinstance(msg, bytes) else json.dumps(msg, separators=(",", ":")).encode()
        return b"Content-Length: %d\r\n\r\n" % len(body) + body

    def raw(self, data):
        """Write bytes as they are (damaged frames, garbage)."""
        os.write(1, data)
        self.log("send", raw=data.decode("latin-1"))

    def send(self, msg):
        self.raw(self.frame(msg))

    def pieces(self, data, sizes, gap=0.05):
        """Write data in pieces of the given sizes (the rest last), gap seconds apart."""
        at = 0
        for n in list(sizes) + [len(data)]:
            if at >= len(data):
                break
            self.raw(data[at:at + n])
            at += n
            time.sleep(gap)

    def reply(self, msg, result):
        self.send({"jsonrpc": "2.0", "id": msg.get("id"), "result": result})

    def notify(self, method, params):
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def die(self, status=0):
        self.log("exit", status=status)
        os._exit(status)

    # ------------------------------------------------------------ positions

    def units(self, line, chars):
        """A column given in characters of line (a str) as the client counts it."""
        if self.chosen == "utf-8":
            return len(line[:chars].encode("utf-8", "surrogateescape"))
        return len(line[:chars].encode("utf-16-le", "surrogatepass")) // 2

    def chars(self, line, units):
        """The other way: a column the client sent, as characters of line."""
        for i in range(len(line) + 1):
            if self.units(line, i) >= units:
                return i
        return len(line)

    def position(self, offset):
        """A character offset into self.text as {"line", "character"} for the client."""
        before = self.text[:offset]
        line = before.count("\n")
        start = before.rfind("\n") + 1
        text = self.text[start:].split("\n", 1)[0]
        return {"line": line, "character": self.units(text, offset - start)}

    def range_of(self, offset, length):
        return {"start": self.position(offset), "end": self.position(offset + length)}

    # ------------------------------------------------------------ the tiny language

    def diagnostics(self):
        out = []
        for word, sev, msg in (("oops", 1, "use of undeclared identifier 'oops'"),
                               ("meh", 2, "unused variable 'meh'")):
            for m in re.finditer(r"\b%s\b" % word, self.text):
                out.append({"range": self.range_of(m.start(), len(word)), "severity": sev,
                            "message": msg, "source": "scripted"})
        return out

    def publish(self):
        if self.diagnose and self.uri:
            self.notify("textDocument/publishDiagnostics",
                        {"uri": self.uri, "version": self.version, "diagnostics": self.diagnostics()})

    def definition(self, params):
        pos = params.get("position", {})
        lines = self.text.split("\n")
        n = pos.get("line", 0)
        if not 0 <= n < len(lines):
            return None
        line = lines[n]
        c = self.chars(line, pos.get("character", 0))
        for m in re.finditer(r"\w+", line):
            if m.start() <= c <= m.end():
                d = re.search(r"\bint\s+(%s)\b" % re.escape(m.group(0)), self.text)
                if d:
                    return [{"uri": self.uri, "range": self.range_of(d.start(1), len(m.group(0)))}]
        return None

    def default(self, msg):
        if msg is None:
            return
        method, mid = msg.get("method"), msg.get("id")
        params = msg.get("params") or {}
        if method == "initialize":
            offered = (((params.get("capabilities") or {}).get("general") or {}).get("positionEncodings")
                       or [])
            enc = self.encoding
            if enc == "auto":
                enc = "utf-8" if offered[:1] == ["utf-8"] else None
            self.chosen = enc or "utf-16"
            caps = dict(self.capabilities)
            if enc:
                caps["positionEncoding"] = enc
            result = {"capabilities": caps}
            if self.server_info is not None:
                result["serverInfo"] = self.server_info
            self.reply(msg, result)
        elif method == "textDocument/didOpen":
            doc = params.get("textDocument", {})
            self.uri, self.text, self.version = doc.get("uri"), doc.get("text", ""), doc.get("version", 0)
            self.publish()
        elif method == "textDocument/didChange":
            changes = params.get("contentChanges") or []
            if changes:
                self.text = changes[-1].get("text", "")
            self.version = params.get("textDocument", {}).get("version", 0)
            self.publish()
        elif method == "textDocument/definition":
            self.reply(msg, self.definition(params))
        elif method == "shutdown":
            self.reply(msg, None)
        elif method == "exit":
            self.die(0)
        elif mid is not None and method:
            self.reply(msg, None)

    # ------------------------------------------------------------ reading

    def messages(self):
        """Each message from the input as (header, body), until it ends."""
        while True:
            while b"\r\n\r\n" in self.buf:
                head, rest = self.buf.split(b"\r\n\r\n", 1)
                m = re.search(rb"(?i)content-length:\s*(\d+)", head)
                n = int(m.group(1)) if m else 0
                if len(rest) < n:
                    break
                self.buf = rest[n:]
                yield head, rest[:n]
            r, _, _ = select.select([0], [], [], 0.5)
            if not r:
                continue
            data = os.read(0, 65536)
            if not data:
                return
            self.buf += data


def watchdog(srv):
    while True:
        time.sleep(0.2)
        if os.getppid() != srv.parent or time.monotonic() - srv.t0 > srv.lifetime:
            srv.log("exit", status=3, why="orphaned or too old")
            os._exit(3)


def open_fds():
    """The descriptors open in this process now (before Python opens any more for its own use),
    each with what it is: "pipe", "devnull", "tty", "file" or "other"."""
    import stat
    null = os.stat(os.devnull)
    out = {}
    for fd in range(0, 256):
        try:
            st = os.fstat(fd)
        except OSError:
            continue
        if stat.S_ISFIFO(st.st_mode):
            out[fd] = "pipe"
        elif os.path.samestat(st, null):
            out[fd] = "devnull"
        elif stat.S_ISCHR(st.st_mode):
            out[fd] = "tty" if os.isatty(fd) else "other"
        elif stat.S_ISREG(st.st_mode):
            out[fd] = "file"
        else:
            out[fd] = "other"
    return out


def main():
    fds = open_fds()
    srv = Server()
    scenario = {}
    path = os.environ.get("KILO_TEST_LSP_SCENARIO")
    if path:
        with open(path) as f:
            code = f.read()
        scenario = {"srv": srv, "time": time, "os": os, "json": json, "signal": signal}
        exec(compile(code, path, "exec"), scenario)
    srv.log("start", pid=os.getpid(), ppid=srv.parent, fds={str(k): v for k, v in fds.items()})
    threading.Thread(target=watchdog, args=(srv,), daemon=True).start()
    if "on_start" in scenario:
        scenario["on_start"](srv)
    if not srv.read:
        while True:
            time.sleep(1)
    for head, body in srv.messages():
        try:
            msg = json.loads(body)
        except ValueError:
            msg = None
        srv.log("recv", header=head.decode("latin-1"), body=body.decode("utf-8", "replace"), msg=msg)
        handled = False
        if "on_message" in scenario:
            handled = scenario["on_message"](srv, msg)
        if not handled:
            srv.default(msg)
    srv.log("eof")
    srv.die(0)


if __name__ == "__main__":
    main()
