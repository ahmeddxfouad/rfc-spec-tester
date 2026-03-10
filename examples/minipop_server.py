from __future__ import annotations
import socketserver

HOST, PORT = "127.0.0.1", 21110

class MiniPOPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        state = "START"
        client = f"{self.client_address[0]}:{self.client_address[1]}"
        print(f"[connect] {client}")
        self.wfile.write(b"+OK MiniPOP ready\r\n")
        print(f"[tx] {client} <- +OK MiniPOP ready")

        while True:
            line = self.rfile.readline()
            if not line:
                print(f"[disconnect] {client}")
                break
            cmdline = line.decode("utf-8", errors="replace").strip()
            if not cmdline:
                continue
            print(f"[rx] {client} -> {cmdline}")
            parts = cmdline.split()
            cmd = parts[0].upper()

            def ok(msg="+OK"):
                self.wfile.write((msg + "\r\n").encode("utf-8"))
                print(f"[tx] {client} <- {msg}")

            def err(msg="-ERR"):
                self.wfile.write((msg + "\r\n").encode("utf-8"))
                print(f"[tx] {client} <- {msg}")

            if cmd == "QUIT":
                ok("+OK")
                break

            if cmd == "USER":
                if len(parts) >= 2:
                    state = "USER_OK"
                    ok("+OK")
                else:
                    err("-ERR missing arg")
                continue

            if cmd == "PASS":
                if state != "USER_OK":
                    err("-ERR bad sequence")
                else:
                    state = "AUTH"
                    ok("+OK")
                continue

            if cmd == "STAT":
                if state != "AUTH":
                    err("-ERR bad sequence")
                else:
                    ok("+OK 2 320")
                continue

            err("-ERR unknown command")

if __name__ == "__main__":
    with socketserver.TCPServer((HOST, PORT), MiniPOPHandler) as server:
        print(f"MiniPOP server listening on {HOST}:{PORT}")
        server.serve_forever()
