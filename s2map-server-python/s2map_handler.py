'''Contain the http request handler for s2map'''

import http.server
import urllib
import logging
import simplejson as json
import s2sphere
from s2 import *


def get_coordinates(cell):
    '''Given the cell, return the coordinates of the cell'''
    points = []
    for i in range(4):
        latlng = s2sphere.LatLng.from_point(cell.get_vertex(i))
        point = {
            "lat": latlng.lat().degrees,
            "lng": latlng.lng().degrees
        }
        points.append(point)
    return points


def get_center(cell):
    '''Given the cell, return the center coord of the cell'''
    ll = s2sphere.LatLng.from_point(cell.get_center())
    return {
        "lat": ll.lat().degrees,
        "lng": ll.lng().degrees
    }


def get_shape_dict(cell_id):
    # redundant, force convertion anyway
    # if not isinstance(cell_id, int):
    #     cell_id = int(cell_id)
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
        "shape": get_coordinates(cell),
    }

    return ret


def get_coords_multi_json(cell_ids):
    ret = []
    for cell_id in cell_ids.split(","):
        if not cell_id or not len(cell_id):
            continue

        r = get_shape_dict(cell_id)
        ret.append(r)

    return bytes(json.dumps(ret, indent=4, sort_keys=True))


class S2Server(http.server.SimpleHTTPRequestHandler):
    '''Request handler for s2map'''

    def extract_arg(self, req_str):
        '''given the request string, return the request argument'''
        temp = self.path[len(req_str):]
        return urllib.unquote(temp)

    def s2info_handler(self, arg):
        response = None
        if arg:
            try:
                response = get_coords_multi_json(arg)
            except ValueError:
                logging.exception("s2info: bad args")
        return response

    def s2cover_handler(self):
        pass

    def fetch_handler(self):
        pass

    def do_GET(self):
        response = None

        if self.path.startswith("/s2info?id="):
            response = self.s2info_handler(self.extract_arg("/s2info?id="))

        if response:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-length", len(response))
            self.end_headers()
            self.wfile.write(response)
        else:
            self.send_response(404)