"""Private worker HTTP transport. All requests require a server-only bearer key."""
import argparse
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .service import Service

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8100)
    parser.add_argument('--bind',default='127.0.0.1')
    parser.add_argument('--data',default='.local/web-data')
    parser.add_argument('--preview',action='store_true')
    args=parser.parse_args()
    token=os.environ.get('PYTHON_API_TOKEN','')
    if len(token)<24: raise SystemExit('Set a server-only PYTHON_API_TOKEN with at least 24 characters.')
    service=Service(args.data,args.preview)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_): pass
        def respond(self,status,payload):
            data=json.dumps(payload,allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Length',str(len(data)))
            self.end_headers(); self.wfile.write(data)
        def dispatch(self):
            if not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token):
                return self.respond(401,{'error':'Authentication required'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if length<0 or length>32768: return self.respond(413,{'error':'Request too large'})
                body=json.loads(self.rfile.read(length) or b'{}')
                if not isinstance(body,dict): raise ValueError('Expected an object')
                result=service.handle(self.command,self.path.strip('/'),body)
                return self.respond(200,result)
            except (ValueError,KeyError,TypeError) as error:
                return self.respond(400,{'error':str(error)[:240]})
            except Exception:
                return self.respond(503,{'error':'The data service is unavailable. Saved lines remain on the server.'})
        do_POST=dispatch
        do_GET=dispatch
        do_DELETE=dispatch
    ThreadingHTTPServer((args.bind,args.port),Handler).serve_forever()

if __name__=='__main__': main()
