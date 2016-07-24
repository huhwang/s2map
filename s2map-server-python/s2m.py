#!/usr/bin/python3

import socketserver
import http.server
import urllib

import json
import s2sphere

import logging

PORT = 1234

def get_shape(cell):
    # get 4 corner points of area
    pts = []
    for i in range(4):
        ll = s2sphere.LatLng.from_point(cell.get_vertex(i))
        pt = {
            "lat": ll.lat().degrees,
            "lng": ll.lng().degrees
        }
        pts.append(pt)

    return pts

def get_center(cell):
    ll = s2sphere.LatLng.from_point(cell.get_center())
    return {
        "lat": ll.lat().degrees,
        "lng": ll.lng().degrees
    }

def get_shape_dict(cell_id):
    if not isinstance(cell_id, int):
        cell_id = int(cell_id)

    cid = s2sphere.CellId(cell_id)
    cell = s2sphere.Cell(cid)

    ret = {
        "id": str(cid.id()),
        "id_signed": str(cid.id()),
        "token": hex(cid.id())[2:-1].strip("0"),
        "pos": 0,
        "face": cell.face(),
        "level": cell.level(),
        "ll": get_center(cell),
        "shape": get_shape(cell),
    }

    return ret

def get_shape_multi_json(cell_ids):
    ret = []
    for cell_id in cell_ids.split(","):
        if not cell_id or not len(cell_id):
            continue

        r = get_shape_dict(cell_id)
        ret.append(r)

    return bytes(json.dumps(ret, indent=4, sort_keys=True), "utf8")

class S2Server(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        response = None

        if self.path.startswith("/s2info?id="):
            arg = self.path[len("/s2info?id="):]
            arg = urllib.parse.unquote(arg)

            if len(arg):
                try:
                    response = get_shape_multi_json(arg)
                except ValueError:
                    logging.exception("s2info: bad args")

        if response:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-length", len(response))
            self.end_headers()
            self.wfile.write(response)
        else:
            self.send_response(404)

if __name__ == "__main__":
    httpd = socketserver.TCPServer(("", PORT), S2Server)
    httpd.allow_reuse_address = True
    print("running on", PORT)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("bye")
        httpd.shutdown()
    except:
        logging.exception("")
        httpd.shutdown()
