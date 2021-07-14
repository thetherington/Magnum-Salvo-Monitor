import datetime
import json
import re
import time

import requests


class salvo_mon:
    def __init__(self, **kwargs):

        self.verbose = None
        self.insite = None
        self.frequency = "5m"
        self.message_id_number = int(time.time())
        self.room_list = []

        for key, value in kwargs.items():

            if "insite" in key and value:

                self.insite = value
                self.url = "http://{}:9200/log-syslog-*/_search/".format(value)

            if "frequency" in key and value:
                self.frequency = value

            if key == "annotate":

                exec("from {} import {}".format(value["module"], value["dict"]), globals())

                self.room_list = eval(value["dict"] + "()")

            if "annotate_db" in key:
                self.room_list = value

        self.query = {
            "size": 10000,
            "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "default_field": "_all",
                                "query": "syslog_program:triton* && salvo && (successful || failed)",
                            }
                        },
                        {"range": {"@timestamp": {"from": "now-{}".format(self.frequency), "to": "now"}}},
                    ]
                }
            },
            "sort": [{"@timestamp": {"order": "asc"}}],
        }

    def fetch(self):

        try:

            response = requests.get(self.url, data=json.dumps(self.query), timeout=30.0)

            return json.loads(response.text)

        except Exception as e:

            with open("salvo_mon", "a+") as f:
                f.write(str(datetime.datetime.now()) + " --- " + "fetch" + "\t" + str(e) + "\r\n")

            return None

    def collect(self):

        results = self.fetch()

        documents = []

        if isinstance(results, dict):

            if "hits" in results.keys():

                for hit in results["hits"]["hits"]:

                    doc = hit["_source"]

                    fields = {
                        "s_type": "salvo_monitor",
                        "s_daemon": doc["syslog_program"],
                        "s_magnum_name": doc["syslog_hostname"],
                        "s_magnum_ip": doc["host"],
                        "t_time": doc["@timestamp"],
                        "s_time_display": self.parse_date(doc["@timestamp"]),
                        "l_msg_id": self.message_id,
                    }

                    for room in self.room_list:
                        if room in doc["syslog_hostname"]:
                            fields.update({"s_pcr": room})

                    if "Salvo successful" in doc["syslog_message"]:

                        fields.update({"s_result": "success"})
                        fields.update(self.parse_success(doc["syslog_message"]))

                        document = {
                            "fields": fields,
                            "host": doc["syslog_hostname"],
                            "name": "salvo_mon",
                        }

                        documents.append(document)

                    elif "Salvo failed" in doc["syslog_message"]:

                        fields.update({"s_result": "failed"})
                        fields.update(self.parse_failure(doc["syslog_message"]))

                        document = {
                            "fields": fields,
                            "host": doc["syslog_hostname"],
                            "name": "salvo_mon",
                        }

                        documents.append(document)

        return documents

    @property
    def message_id(self):

        self.message_id_number += 1

        return self.message_id_number

    def parse_date(self, date_str):

        try:

            dt = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            dt = dt - datetime.timedelta(hours=4)

            return dt.strftime("%b %d %H:%M:%S EST")

        except Exception:
            pass

    def parse_success(self, message):

        fields = {}

        for key in ["Salvo", "User", "Address"]:

            modulePattern = re.compile(key + r" \[(.*?)\]")

            matchValue = modulePattern.finditer(message)

            for match in matchValue:
                fields.update({key.lower(): match.group(1)})

        return fields

    def parse_failure(self, message):

        fields = {}

        overrides = {"Salvo": "salvo", "User": "as_errors", "Address": "user", "Error": "address"}

        for key in ["Salvo", "User", "Address", "Error"]:

            modulePattern = re.compile(key + r" \[(.*?)\]")

            matchValue = modulePattern.finditer(message)

            for match in matchValue:

                if key == "User":

                    try:

                        errors = match.group(1).replace("[", "").replace("'", "").split(", ")
                        fields.update({overrides[key]: errors, "i_num_issues": len(errors)})

                    except Exception:

                        fields.update({overrides[key].replace("as", "s"): match.group(1).replace("[", "").replace("'", "")})

                else:
                    fields.update({overrides[key]: match.group(1)})

        return fields


def main():

    params = {
        "insite": "172.16.205.201",
        "frequency": "2h",
        "annotate": {"module": "ThirtyRock_PROD_edge_def", "dict": "return_roomlist"},
    }

    collector = salvo_mon(**params)

    # print(json.dumps(collector.fetch(), indent=2))
    print(json.dumps(collector.collect(), indent=2))


if __name__ == "__main__":
    main()
