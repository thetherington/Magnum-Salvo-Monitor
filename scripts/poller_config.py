import json
from magnum_salvo import salvo_mon
from insite_plugin import InsitePlugin


class Plugin(InsitePlugin):
    def can_group(self):
        return False

    def fetch(self, hosts):

        try:

            self.collector

        except Exception:

            # control room annotation file
            # from ThirtyRock_PROD_edge_def import return_roomlist

            params = {
                "insite": "172.16.205.201",
                "frequency": "5m",
                # "annotate_db": return_roomlist(),
            }

            self.collector = salvo_mon(**params)

        return json.dumps(self.collector.collect())
