'''Contain the http request handler for s2map'''

import simplejson as json
import http.server
import urllib
import logging

from s2 import *


def get_formated_latlng(point):
    '''Given the S2Point obj, return the formated latlng dict'''
    latlng = S2LatLng(point)
    return {
        "lat": latlng.lat().degrees(),
        "lng": latlng.lng().degrees()
    }


def get_vertices(cell):
    '''Given the cell, return 4 vertex coordinates of the cell'''
    points = []
    for i in range(4):
        point = get_formated_latlng(cell.GetVertex(i))
        points.append(point)
    return points


def get_center(cell):
    '''Given the cell, return the center coord of the cell'''
    return get_formated_latlng(cell.GetCenter())


def get_formated_dict_from_s2cellid(cellid):
    '''given the s2cellid, return the formated dict of that cell'''
    cell = S2Cell(cellid)
    return {
        "id": str(cellid.id()),
        # convert this to ctype long??? see if it works first
        "id_signed": str(cellid.id()),
        "token": cellid.ToToken(),
        "pos": cellid.pos(),
        "face": cell.level(),
        "level": cell.level(),
        "ll": get_center(cell),
        "shape": get_vertices(cell),
    }


def get_coords_multi_json(arg):
    ret = []
    cell_ids = arg['id']
    for cell_id in cell_ids.split(","):
        if not cell_id or not len(cell_id):
            continue

        r = ''
        # r = get_shape_dict(cell_id)
        ret.append(r)

    return bytes(json.dumps(ret, indent=4, sort_keys=True))


class S2Server(http.server.SimpleHTTPRequestHandler):
    '''Request handler for s2map'''

    def extract_arg(self, arg_str):
        '''given the request string, return the request argument dict'''
        # first, find the position of \?\ If found, means this is a arg str of GET,
        # otherwise this is of POST. Either way the action afterwards is the
        # same.
        pos = arg_str.find('?')
        if pos >= 0:
            arg_str = arg_str[pos:]
        arg_str = urllib.unquote(arg_str)

        # store argument kv pair into dict
        arg_dict = dict()
        for req_str in arg_str.split("&"):
            pos = req_str.find('=')
            arg_dict[req_str[:pos]] = req_str[pos + 1:]
        return arg_dict

    def s2info_handler(self, arg):
        response = None
        if not arg:
            return response
        try:
            response = get_coords_multi_json(arg)
        except ValueError:
            logging.exception("s2info: bad args")
        return response

    def s2cover_handler(self, arg):
        if not arg:
            return None

        # create a point list
        points_str = arg['points']
        i = temp = 0
        s2pt_list = []
        for point_coord in points_str.split(','):
            if i % 2:
                latlng = S2LatLng.FromDegrees(temp, float(point_coord))
                s2pt_list.append(latlng.ToPoint())
            else:
                temp = float(point_coord)
            i = i + 1
        print 'num points:', len(s2pt_list)

        # handle one point case
        if len(s2pt_list) == 1:
            region = S2LatLngRect.FromPoint(S2LatLng(s2pt_list[0]))
        else:
            builder = S2PolygonBuilder(S2PolygonBuilderOptions.DIRECTED_XOR())
            length = len(s2pt_list)
            for i in range(0, length):
                builder.AddEdge(s2pt_list[i], s2pt_list[(i + 1) % length])
            success, region, unused_edge = builder.AssemblePolygon()
            if not success:
                return None

        # not checked. Assumed min < max & both min & max >=0 <=30
        min_level = int(arg['min_level'])
        max_level = int(arg['max_level'])
        level_mod = int(arg['level_mod'])
        max_cells = int(arg['max_cells'])

        print 'minlevel', min_level
        print 'maxlevel', max_level
        print 'levelmod', level_mod
        print 'maxcells', max_cells

        coverer = S2RegionCoverer()
        coverer.set_min_level(min_level)
        coverer.set_max_level(max_level)
        coverer.set_level_mod(level_mod)
        coverer.set_max_cells(max_cells)
        covering = coverer.GetCovering(region)

        response_raw = []
        for cellid in covering:
            response_raw.append(get_formated_dict_from_s2cellid(cellid))
        return bytes(json.dumps(response_raw, indent=4, sort_keys=True))

    def fetch_handler(self):
        pass

    def s2mapapi_handler(self, req, arg):
        '''handle different api requests'''
        # req: str
        # arg: dict
        print 'handling s2mapapi request...'
        response = None
        if req.startswith("/s2info"):
            print 'handling s2info...'
            response = self.s2info_handler(arg)
        elif req.startswith("/s2cover"):
            print 'handling s2cover...'
            response = self.s2cover_handler(arg)
        elif req.startswith("/fetch"):
            print 'handling fetch...'
            pass

        if response:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-length", len(response))
            self.end_headers()
            self.wfile.write(response)
        else:
            self.send_response(404)

    def do_GET(self):
        '''handle get req'''
        print 'GET'
        # process s2map api req
        if self.path.startswith("/s2mapapi"):
            api_arg = self.path[len('/s2mapapi'):]
            self.s2mapapi_handler(api_arg, self.extract_arg(api_arg))
        # anything else serve as standard get req
        else:
            f = self.send_head()
            if f:
                try:
                    self.copyfile(f, self.wfile)
                finally:
                    f.close()

    def do_POST(self):
        '''handle post req'''
        print 'POST'
        # get the actual content of the post request
        length = int(self.headers.getheader('content-length'))
        arg_str = self.rfile.read(length)

        # process s2map api rep
        if self.path.startswith("/s2mapapi"):
            self.s2mapapi_handler(
                self.path[len('/s2mapapi'):], self.extract_arg(arg_str))
        # otherwise don't know what to do, send back 404 error
        else:
            self.send_error(404)
