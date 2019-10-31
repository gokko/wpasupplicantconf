from collections import OrderedDict
import json

class ParseError(ValueError):
    pass


class WpaSupplicantConf:
    """This class parses a wpa_supplicant configuration file, allows
    manipulation of the configured networks and then writing out of
    the updated file.

    WARNING: Although care has been taken to preserve ordering,
    comments will be lost for any wpa_supplicant.conf which is
    round-tripped through this class.
    """

    def __init__(self, lines):
        self._fields = OrderedDict()
        self._networks = OrderedDict()

        network = None
        for line in lines.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if line == "}":
                if network is None:
                    raise ParseError("unxpected '}'")

                ssid = network.pop('ssid', None)
                if ssid is None:
                    raise ParseError('missing "ssid" for network')
                self._networks[dequote(ssid)] = network
                network = None
                continue

            parts = [x.strip() for x in line.split('=', 1)]
            if len(parts) != 2:
                raise ParseError("invalid line: %{!r}".format(line))

            left, right = parts

            if right == '{':
                if left != 'network':
                    raise ParseError('unsupported section: "{}"'.format(left))
                if network is not None:
                    raise ParseError("can't nest networks")

                network = OrderedDict()
            else:
                if network is None:
                    self._fields[left] = right
                else:
                    network[left] = right

    def fields(self):
        return self._fields

    def networks(self):
        return self._networks

    def add_network(self, ssid, **attrs):
        self._networks[ssid] = attrs

    def remove_network(self, ssid):
        self._networks.pop(ssid, None)

    def write(self, f):
        needClose= False
        if type(f) == str:
            f= open(f, 'w')
            needClose= True
        for name, value in self._fields.items():
            f.write("{}={}\n".format(name, value))

        for ssid, info in self._networks.items():
            f.write("\nnetwork={\n")
            f.write('    ssid="{}"\n'.format(ssid))
            for name, value in info.items():
                f.write("    {}={}\n".format(name, value))
            f.write("}\n")
        if needClose:
            f.close()

    def toJson(self):
        res= {}
        for field in self.fields():
            res[field]= self.fields()[field]
        nets= []
        for network in self.networks():
            net= {}
            net['ssid']= network
            params= self.networks()[network]
            for param in params:
                net[param]= params[param]
            nets.append(net)
        res['networks']= nets
        return json.dumps(res)

    def readJson(self, inJson):
        if type(inJson)== str:
            inJson= json.loads(inJson)
        for field in inJson:
            if field != 'networks':
                self._fields[field] = inJson[field]
        for network in inJson['networks']:
            ssid= network.pop('ssid', None)
            self._networks[ssid]= network

def dequote(v):
    if len(v) < 2:
        return v
    if v.startswith('"') and v.endswith('"'):
        return v[1:-1]
    return v
